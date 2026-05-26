"""Embedding backend selector.

Both implementations honour LangChain's Embeddings interface (embed_documents,
embed_query), so callers in ingestion and retrieval are backend-agnostic.

Backend is chosen by the EMBEDDING_BACKEND env var:

- 'local' (default): BAAI/bge-small-en-v1.5 via HuggingFace, runs in-process.
  Free, no API key needed, slow on small CPUs.
- 'cohere': embed-english-v3.0 over HTTPS. Free tier (1000 req/min), ~50ms
  per query, much faster than local on resource-constrained hosts.

The two backends produce different vector dimensions (384 vs 1024), so the
Chroma index must be rebuilt when switching. Run scripts/ingest.py --clear
after changing EMBEDDING_BACKEND.
"""
from __future__ import annotations

from langchain_core.embeddings import Embeddings

from rag.config import (
    COHERE_API_KEY,
    COHERE_EMBEDDING_MODEL,
    EMBEDDING_BACKEND,
    EMBEDDING_MODEL,
)


def get_embedder() -> Embeddings:
    """Return an embeddings client based on EMBEDDING_BACKEND."""
    if EMBEDDING_BACKEND == "cohere":
        return _build_cohere()
    return _build_local()


def _build_local() -> Embeddings:
    from langchain_huggingface import HuggingFaceEmbeddings

    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        encode_kwargs={"normalize_embeddings": True},
    )


def _build_cohere() -> Embeddings:
    from langchain_cohere import CohereEmbeddings

    if not COHERE_API_KEY:
        raise RuntimeError(
            "EMBEDDING_BACKEND=cohere requires COHERE_API_KEY in the environment. "
            "Get a free trial key at https://dashboard.cohere.com/api-keys"
        )

    return CohereEmbeddings(
        model=COHERE_EMBEDDING_MODEL,
        cohere_api_key=COHERE_API_KEY,
    )
