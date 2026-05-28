"""Retrieval-quality comparison: bi-encoder only vs bi-encoder + reranker.

For each question in evaluation/questions.json, retrieve k=5 chunks both
ways and check whether the expected document ID appears in the result —
and at what rank. Reports recall@5 and mean reciprocal rank (MRR@5) for
each configuration plus a delta.

This is a retrieval-only measurement (no LLM calls), so it doesn't burn
Groq quota. Cohere reranker costs ~25 calls per run from this script.

Usage:
    PYTHONPATH=. python scripts/rerank_compare.py
    PYTHONPATH=. python scripts/rerank_compare.py --reranker local
    PYTHONPATH=. python scripts/rerank_compare.py --candidates 30 --top-k 5
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from rag.config import RERANK_CANDIDATE_K, TOP_K
from rag.retrieval import Retriever


def _rank_of_expected(
    results: list, expected_doc_id: str
) -> int | None:
    """1-indexed rank of the expected doc, or None if not in results."""
    for i, (doc, _score) in enumerate(results, start=1):
        if doc.metadata.get("doc_id") == expected_doc_id:
            return i
    return None


def _evaluate(retriever: Retriever, questions: list[dict], top_k: int) -> dict:
    hits = 0
    rr_sum = 0.0  # reciprocal-rank sum, for MRR
    in_corpus_total = 0
    per_question = []
    t0 = time.time()

    for q in questions:
        if not q.get("in_corpus", True):
            continue
        in_corpus_total += 1
        results = retriever.retrieve(q["question"], k=top_k)
        rank = _rank_of_expected(results, q["expected_doc_id"])
        if rank is not None:
            hits += 1
            rr_sum += 1.0 / rank
        per_question.append({"id": q["id"], "rank": rank})

    elapsed = time.time() - t0
    return {
        "recall_at_k": hits / in_corpus_total if in_corpus_total else 0.0,
        "mrr_at_k": rr_sum / in_corpus_total if in_corpus_total else 0.0,
        "total_questions": in_corpus_total,
        "hits": hits,
        "elapsed_seconds": elapsed,
        "per_question": per_question,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reranker",
        choices=("cohere", "local"),
        default="cohere",
        help="Which reranker backend to compare against bi-encoder-only.",
    )
    parser.add_argument(
        "--candidates",
        type=int,
        default=RERANK_CANDIDATE_K,
        help="First-stage candidate set size when reranking.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=TOP_K,
        help="Final retrieved chunk count.",
    )
    args = parser.parse_args()

    questions_path = ROOT / "evaluation" / "questions.json"
    questions = json.loads(questions_path.read_text())

    # Baseline: bi-encoder only.
    print(f"\n== Baseline (no reranker, k={args.top_k}) ==")
    baseline_retriever = Retriever(k=args.top_k, reranker=None)
    baseline = _evaluate(baseline_retriever, questions, args.top_k)
    print(
        f"recall@{args.top_k}={baseline['recall_at_k']:.3f}  "
        f"mrr@{args.top_k}={baseline['mrr_at_k']:.3f}  "
        f"hits={baseline['hits']}/{baseline['total_questions']}  "
        f"elapsed={baseline['elapsed_seconds']:.1f}s"
    )

    # With reranker.
    print(
        f"\n== With reranker ({args.reranker}, "
        f"candidates={args.candidates} → top-{args.top_k}) =="
    )
    # Build the reranker explicitly so we don't depend on env var state.
    from rag.reranker import _CohereReranker, _LocalReranker

    reranker = (
        _CohereReranker() if args.reranker == "cohere" else _LocalReranker()
    )
    rerank_retriever = Retriever(
        k=args.top_k, reranker=reranker, candidate_k=args.candidates
    )
    reranked = _evaluate(rerank_retriever, questions, args.top_k)
    print(
        f"recall@{args.top_k}={reranked['recall_at_k']:.3f}  "
        f"mrr@{args.top_k}={reranked['mrr_at_k']:.3f}  "
        f"hits={reranked['hits']}/{reranked['total_questions']}  "
        f"elapsed={reranked['elapsed_seconds']:.1f}s"
    )

    print("\n== Delta ==")
    d_recall = reranked["recall_at_k"] - baseline["recall_at_k"]
    d_mrr = reranked["mrr_at_k"] - baseline["mrr_at_k"]
    d_time_per_q = (
        reranked["elapsed_seconds"] - baseline["elapsed_seconds"]
    ) / max(reranked["total_questions"], 1)
    print(
        f"recall@{args.top_k}: {d_recall:+.3f}  "
        f"mrr@{args.top_k}: {d_mrr:+.3f}  "
        f"per-query overhead: {d_time_per_q * 1000:+.0f}ms"
    )


if __name__ == "__main__":
    main()
