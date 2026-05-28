"""Ad-hoc tester for the RAG pipeline.

Usage:
    PYTHONPATH=. python scripts/ask.py "What is the daily limit for a Tier-3 agent?"
    PYTHONPATH=. python scripts/ask.py --debug "..."
    PYTHONPATH=. python scripts/ask.py --json "..."
    PYTHONPATH=. python scripts/ask.py --stream "..."
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rag.pipeline import RAGPipeline


def _run_stream(pipeline: RAGPipeline, question: str, debug: bool) -> None:
    print(f"\nQ: {question}\n\nA: ", end="", flush=True)
    final: dict | None = None
    for event in pipeline.stream_answer(question):
        if "token" in event:
            print(event["token"], end="", flush=True)
        elif event.get("done"):
            final = event
    print()  # newline after the streamed answer

    if final is None:
        return

    print(f"\nCitations ({len(final['citations'])}):")
    for c in final["citations"]:
        print(f"  [Source {c['source_idx']}] {c['doc_id']} | {c['section']}")

    print(
        f"\nTiming: retrieve={final['retrieve_ms']}ms, "
        f"generate={final['generate_ms']}ms, "
        f"total={final['total_ms']}ms"
    )

    if debug:
        print("\nRetrieval debug:")
        for r in final["retrieval_debug"]:
            print(
                f"  [{r['source_idx']}] dist={r['distance']:.4f}  "
                f"{r['doc_id']} | {r['section']}"
            )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question", nargs="+", help="The question to ask.")
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Show retrieval distances for every chunk returned.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the full result payload as JSON.",
    )
    parser.add_argument(
        "--stream",
        action="store_true",
        help="Stream the answer token-by-token as the LLM produces it.",
    )
    args = parser.parse_args()

    question = " ".join(args.question)

    pipeline = RAGPipeline()

    if args.stream:
        _run_stream(pipeline, question, args.debug)
        return

    result = pipeline.answer(question)

    if args.json:
        print(json.dumps(result, indent=2))
        return

    print(f"\nQ: {question}")

    if result["out_of_corpus"]:
        print("\n[Out of corpus]")
        print(result["answer"])
    else:
        print(f"\nA: {result['answer']}")

    print(f"\nCitations ({len(result['citations'])}):")
    for c in result["citations"]:
        print(f"  [Source {c['source_idx']}] {c['doc_id']} | {c['section']}")

    print(
        f"\nTiming: retrieve={result['retrieve_ms']}ms, "
        f"generate={result['generate_ms']}ms, "
        f"total={result['total_ms']}ms"
    )

    if args.debug:
        print("\nRetrieval debug:")
        for r in result["retrieval_debug"]:
            print(
                f"  [{r['source_idx']}] dist={r['distance']:.4f}  "
                f"{r['doc_id']} | {r['section']}"
            )


if __name__ == "__main__":
    main()
