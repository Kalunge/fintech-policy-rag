"""Run the RAG pipeline against the eval set and produce a metrics report.

Usage:
    PYTHONPATH=. python scripts/evaluate.py
    PYTHONPATH=. python scripts/evaluate.py --questions evaluation/questions.json
    PYTHONPATH=. python scripts/evaluate.py --out evaluation/results.json
    PYTHONPATH=. python scripts/evaluate.py --quick           # use first 5 questions only
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from evaluation.metrics import (
    correct_policy_cited,
    correct_refusal,
    judge,
    partial_match,
)
from rag.generation import get_llm
from rag.pipeline import RAGPipeline


def load_questions(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    return statistics.quantiles(values, n=100, method="inclusive")[int(p) - 1]


def evaluate(questions: list[dict]) -> dict:
    pipeline = RAGPipeline()
    judge_llm = get_llm(temperature=0.0, max_tokens=400)

    in_corpus = [q for q in questions if q.get("in_corpus", True)]
    out_of_corpus = [q for q in questions if not q.get("in_corpus", True)]

    print(f"Loaded {len(questions)} questions ({len(in_corpus)} in-corpus, {len(out_of_corpus)} out-of-corpus)")
    print("Warming pipeline...")
    pipeline.retriever.retrieve("warmup", k=1)
    print()

    per_question_results: list[dict] = []
    latencies: list[float] = []

    for i, q in enumerate(questions, start=1):
        print(f"[{i}/{len(questions)}] {q['id']}: {q['question'][:80]}")
        result = pipeline.answer(q["question"])
        latencies.append(result["total_ms"])

        entry: dict = {
            "id": q["id"],
            "question": q["question"],
            "in_corpus": q.get("in_corpus", True),
            "answer": result["answer"],
            "citations": result["citations"],
            "out_of_corpus_pipeline": result["out_of_corpus"],
            "retrieve_ms": result["retrieve_ms"],
            "generate_ms": result["generate_ms"],
            "total_ms": result["total_ms"],
        }

        if q.get("in_corpus", True):
            try:
                judgment = judge(
                    q["question"],
                    result["answer"],
                    result["citations"],
                    # Use the un-truncated chunk content so the judge can verify
                    # claims that appear past the UI snippet's 320-char cutoff.
                    result.get("full_chunks") or result["snippets"],
                    judge_llm=judge_llm,
                )
            except Exception as exc:
                judgment = {
                    "grounded": False,
                    "grounded_reasoning": f"judge error: {exc}",
                    "citations_accurate": False,
                    "citations_reasoning": f"judge error: {exc}",
                }
            entry["judge"] = judgment
            entry["correct_policy_cited"] = correct_policy_cited(
                result["citations"], q.get("expected_doc_id")
            )
            entry["partial_match"] = partial_match(
                result["answer"], q.get("must_contain")
            )
            print(
                f"    grounded={judgment['grounded']}  "
                f"citations_accurate={judgment['citations_accurate']}  "
                f"policy_match={entry['correct_policy_cited']}  "
                f"partial={entry['partial_match']['score']:.2f}  "
                f"({result['total_ms']:.0f}ms)"
            )
        else:
            entry["correct_refusal"] = correct_refusal(result["answer"])
            print(
                f"    correct_refusal={entry['correct_refusal']}  "
                f"({result['total_ms']:.0f}ms)"
            )

        per_question_results.append(entry)

    # Aggregates
    ic = [r for r in per_question_results if r["in_corpus"]]
    ooc = [r for r in per_question_results if not r["in_corpus"]]

    grounded_count = sum(1 for r in ic if r.get("judge", {}).get("grounded"))
    cites_count = sum(1 for r in ic if r.get("judge", {}).get("citations_accurate"))
    policy_count = sum(1 for r in ic if r.get("correct_policy_cited"))
    full_partial = sum(1 for r in ic if r.get("partial_match", {}).get("score", 0) == 1.0)
    refusal_count = sum(1 for r in ooc if r.get("correct_refusal"))

    summary = {
        "total_questions": len(questions),
        "in_corpus": {
            "n": len(ic),
            "groundedness_pct": round(grounded_count / max(len(ic), 1) * 100, 1),
            "citation_accuracy_pct": round(cites_count / max(len(ic), 1) * 100, 1),
            "correct_policy_cited_pct": round(policy_count / max(len(ic), 1) * 100, 1),
            "full_partial_match_pct": round(full_partial / max(len(ic), 1) * 100, 1),
        },
        "out_of_corpus": {
            "n": len(ooc),
            "correct_refusal_pct": round(refusal_count / max(len(ooc), 1) * 100, 1),
        },
        "latency_ms": {
            "p50": round(percentile(latencies, 50), 1) if len(latencies) >= 2 else round(latencies[0], 1) if latencies else 0.0,
            "p95": round(percentile(latencies, 95), 1) if len(latencies) >= 2 else round(latencies[0], 1) if latencies else 0.0,
            "min": round(min(latencies), 1) if latencies else 0.0,
            "max": round(max(latencies), 1) if latencies else 0.0,
            "mean": round(sum(latencies) / max(len(latencies), 1), 1),
            "samples": len(latencies),
        },
    }

    return {"summary": summary, "results": per_question_results}


def print_report(report: dict) -> None:
    s = report["summary"]
    ic, ooc, lat = s["in_corpus"], s["out_of_corpus"], s["latency_ms"]

    print()
    print("=" * 64)
    print("EVALUATION REPORT")
    print("=" * 64)
    print(f"  Total questions: {s['total_questions']}")
    print()
    print(f"  In-corpus ({ic['n']} questions):")
    print(f"    Groundedness            {ic['groundedness_pct']:>5.1f}%")
    print(f"    Citation accuracy       {ic['citation_accuracy_pct']:>5.1f}%")
    print(f"    Correct policy cited    {ic['correct_policy_cited_pct']:>5.1f}%")
    print(f"    Full partial match      {ic['full_partial_match_pct']:>5.1f}%")
    print()
    print(f"  Out-of-corpus ({ooc['n']} questions):")
    print(f"    Correct refusal         {ooc['correct_refusal_pct']:>5.1f}%")
    print()
    print(f"  Latency (over {lat['samples']} queries):")
    print(f"    p50  {lat['p50']:>7.1f} ms")
    print(f"    p95  {lat['p95']:>7.1f} ms")
    print(f"    min  {lat['min']:>7.1f} ms")
    print(f"    max  {lat['max']:>7.1f} ms")
    print(f"    mean {lat['mean']:>7.1f} ms")
    print("=" * 64)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--questions",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "evaluation" / "questions.json",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "evaluation" / "results.json",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run only the first 5 questions (for a fast sanity check).",
    )
    args = parser.parse_args()

    questions = load_questions(args.questions)
    if args.quick:
        questions = questions[:5]

    t0 = time.time()
    report = evaluate(questions)
    report["wall_seconds"] = round(time.time() - t0, 1)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print_report(report)
    print(f"\nFull results saved to: {args.out}")
    print(f"Wall clock: {report['wall_seconds']}s")


if __name__ == "__main__":
    main()
