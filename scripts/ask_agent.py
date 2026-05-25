"""Ad-hoc tester for the agentic pipeline (RAG + banking tools).

Usage:
    PYTHONPATH=. python scripts/ask_agent.py "What is the float balance for AG-001?"
    PYTHONPATH=. python scripts/ask_agent.py --json "..."
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rag.agent import AgenticPipeline


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question", nargs="+", help="The question to ask.")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the full result payload as JSON.",
    )
    args = parser.parse_args()

    question = " ".join(args.question)

    pipeline = AgenticPipeline()
    result = pipeline.answer(question)

    if args.json:
        print(json.dumps(result, indent=2, default=str))
        return

    print(f"\nQ: {question}")
    print(f"\nA: {result['answer']}")

    if result["tool_calls"]:
        print(f"\nTool calls ({len(result['tool_calls'])}):")
        for tc in result["tool_calls"]:
            print(f"  - {tc['tool']}({tc['args']}) → {tc['summary']}")

    if result["citations"]:
        print(f"\nCitations ({len(result['citations'])}):")
        for c in result["citations"]:
            print(f"  [Source {c['source_idx']}] {c['doc_id']} | {c['section']}")

    print(
        f"\nTiming: retrieve={result['retrieve_ms']}ms, "
        f"generate={result['generate_ms']}ms, "
        f"total={result['total_ms']}ms ({result['iterations']} iterations)"
    )


if __name__ == "__main__":
    main()
