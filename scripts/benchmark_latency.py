"""Measure honest interactive latency without judge-call interference.

The full eval (`scripts/evaluate.py`) makes 50 LLM calls in ~2.5 minutes which
saturates Groq's free-tier rate limit and inflates latency. This script
instead:

- Calls the RAG pipeline only (no LLM-as-judge)
- Pauses between queries to mimic real interactive use
- Reports retrieve / generate / total percentiles separately

Usage:
    PYTHONPATH=. python scripts/benchmark_latency.py
    PYTHONPATH=. python scripts/benchmark_latency.py --queries 20 --pause 1.5
    PYTHONPATH=. python scripts/benchmark_latency.py --out evaluation/latency.json
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rag.pipeline import RAGPipeline


SAMPLE_QUESTIONS = [
    "What is the maximum session length for privileged access?",
    "How long does ThaBytePay take to remediate critical vulnerabilities?",
    "What is the minimum password length policy?",
    "How long are KYC documents retained after account closure?",
    "Within what timeframe must a data breach be reported to the regulator?",
    "What is the daily transaction limit for a Tier-3 agent?",
    "What is the minimum float that a Master Agent must maintain?",
    "How often are POS PIN encryption keys rotated?",
    "When must a stolen card be reported?",
    "What is the standard card validity period?",
    "What is the balance limit for a Tier-1 KYC account?",
    "What is the SEV1 response SLA?",
    "When is a post-incident review held?",
    "What is the monthly home-office allowance for remote employees?",
    "What approval is needed to spend 800,000 KES?",
    "What is the threshold for declaring a gift from a customer?",
    "What is the Recovery Time Objective for mobile banking?",
    "What activities are prohibited for agents?",
    "What must employees do if a Group laptop is lost or stolen?",
    "How often are high-risk customer relationships reviewed?",
]


def percentile(values: list[float], p: float) -> float:
    if len(values) < 2:
        return values[0] if values else 0.0
    return statistics.quantiles(values, n=100, method="inclusive")[int(p) - 1]


def summarize(label: str, values: list[float]) -> dict:
    return {
        "label": label,
        "n": len(values),
        "p50": round(percentile(values, 50), 1),
        "p95": round(percentile(values, 95), 1),
        "min": round(min(values), 1) if values else 0.0,
        "max": round(max(values), 1) if values else 0.0,
        "mean": round(sum(values) / max(len(values), 1), 1),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--queries",
        type=int,
        default=20,
        help="How many queries to run (default 20).",
    )
    parser.add_argument(
        "--pause",
        type=float,
        default=1.5,
        help="Seconds to wait between queries (default 1.5).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "evaluation" / "latency.json",
    )
    args = parser.parse_args()

    questions = SAMPLE_QUESTIONS[: args.queries]
    print(f"Running {len(questions)} queries with {args.pause}s pause between each.")
    print()

    pipeline = RAGPipeline()
    print("Warming pipeline...")
    pipeline.retriever.retrieve("warmup", k=1)
    print()

    # Discard the first query — it includes residual cold-start cost.
    retrieve_ms: list[float] = []
    generate_ms: list[float] = []
    total_ms: list[float] = []

    for i, q in enumerate(questions, start=1):
        if i > 1:
            time.sleep(args.pause)

        result = pipeline.answer(q)
        retrieve_ms.append(result["retrieve_ms"])
        generate_ms.append(result["generate_ms"])
        total_ms.append(result["total_ms"])

        flag = " (warmup, excluded from stats)" if i == 1 else ""
        print(
            f"[{i:>2}/{len(questions)}] "
            f"retrieve={result['retrieve_ms']:>6.1f}ms  "
            f"generate={result['generate_ms']:>7.1f}ms  "
            f"total={result['total_ms']:>7.1f}ms{flag}"
        )

    # Drop the first sample from summary statistics.
    retrieve_stats = summarize("retrieve_ms", retrieve_ms[1:])
    generate_stats = summarize("generate_ms", generate_ms[1:])
    total_stats = summarize("total_ms", total_ms[1:])

    report = {
        "queries": len(questions),
        "pause_seconds": args.pause,
        "retrieve_ms": retrieve_stats,
        "generate_ms": generate_stats,
        "total_ms": total_stats,
        "raw_total_ms": total_ms,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print()
    print("=" * 64)
    print("LATENCY BENCHMARK (interactive, no judge, first sample excluded)")
    print("=" * 64)
    for stats in (retrieve_stats, generate_stats, total_stats):
        print(
            f"  {stats['label']:<14}  "
            f"p50={stats['p50']:>7.1f}ms  "
            f"p95={stats['p95']:>7.1f}ms  "
            f"mean={stats['mean']:>7.1f}ms  "
            f"min={stats['min']:>7.1f}ms  "
            f"max={stats['max']:>7.1f}ms"
        )
    print("=" * 64)
    print(f"\nSaved to: {args.out}")


if __name__ == "__main__":
    main()
