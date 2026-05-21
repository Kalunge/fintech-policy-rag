"""Build the Chroma vector store from the policy corpus.

Usage:
    PYTHONPATH=. python scripts/ingest.py            # incremental build (skips if dir exists)
    PYTHONPATH=. python scripts/ingest.py --clear    # rebuild from scratch
"""
import argparse
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rag.config import CHROMA_DIR, CHUNK_OVERLAP, CHUNK_SIZE, CORPUS_DIR, TOP_K
from rag.ingestion import build_index, load_and_chunk


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Delete the existing Chroma directory before building.",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("Ingesting fintech policy corpus")
    print("=" * 60)
    print(f"  Corpus dir       : {CORPUS_DIR}")
    print(f"  Chroma dir       : {CHROMA_DIR}")
    print(f"  Chunk size       : {CHUNK_SIZE} tokens")
    print(f"  Chunk overlap    : {CHUNK_OVERLAP} tokens")
    print(f"  Top-K (runtime)  : {TOP_K}")
    print(f"  Clear existing   : {args.clear}")
    print()

    t0 = time.time()
    print("[1/2] Loading and chunking documents...")
    chunks = load_and_chunk()
    t_chunk = time.time() - t0
    print(f"      {len(chunks)} chunks produced in {t_chunk:.1f}s")

    sources = Counter(c.metadata.get("source", "?") for c in chunks)
    print()
    print("      Chunks per source document:")
    for source, count in sorted(sources.items()):
        print(f"        {source}: {count}")

    print()
    t1 = time.time()
    print("[2/2] Embedding and persisting to Chroma...")
    store = build_index(chunks, clear_existing=args.clear)
    t_embed = time.time() - t1
    print(f"      Index built in {t_embed:.1f}s")

    print()
    print(f"Total ingestion time: {time.time() - t0:.1f}s")
    print()

    # Sanity check: try a couple of queries
    print("=" * 60)
    print("Sanity check retrievals (top-3)")
    print("=" * 60)
    sample_queries = [
        "How often are POS PIN encryption keys rotated?",
        "What is the daily transaction limit for a Tier-3 agent?",
        "When must a data breach be reported to the regulator?",
    ]
    for q in sample_queries:
        print(f"\nQ: {q}")
        results = store.similarity_search(q, k=3)
        for i, r in enumerate(results, 1):
            section = r.metadata.get("section", "?")
            doc_id = r.metadata.get("doc_id", "?")
            preview = r.page_content[:140].replace("\n", " ")
            print(f"  [{i}] {doc_id} | {section}")
            print(f"      {preview}...")


if __name__ == "__main__":
    main()
