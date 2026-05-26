"""Top-k similarity retrieval over the persisted Chroma collection."""
from __future__ import annotations

from langchain_core.documents import Document

from rag.config import EMBEDDING_BACKEND, TOP_K
from rag.ingestion import load_vectorstore


class EmbeddingDimensionMismatch(RuntimeError):
    """The Chroma index was built with a different embedding backend than
    the one currently configured. The user must either switch backends or
    rebuild the index."""


class Retriever:
    """Wraps the vector store to expose a simple top-k search interface.

    Returns chunks alongside their cosine distances so downstream
    guardrails can decide whether the question is in-scope.
    """

    def __init__(self, k: int = TOP_K):
        self.k = k
        self.vectorstore = load_vectorstore()

    def retrieve(self, query: str, k: int | None = None) -> list[tuple[Document, float]]:
        """Return the top-k most similar chunks with their distance scores.

        Chroma reports distances where 0 = identical and ~2 = opposite for
        normalized cosine similarity.
        """
        k = k or self.k
        try:
            return self.vectorstore.similarity_search_with_score(query, k=k)
        except Exception as exc:
            msg = str(exc)
            if "dimension" in msg.lower():
                raise EmbeddingDimensionMismatch(
                    f"The Chroma index was built with a different embedding model "
                    f"than the one currently configured (EMBEDDING_BACKEND="
                    f"{EMBEDDING_BACKEND!r}). Rebuild the index by running:\n\n"
                    f"    PYTHONPATH=. python scripts/ingest.py --clear\n\n"
                    f"(make sure EMBEDDING_BACKEND is set to the same value during "
                    f"ingestion and during the API server run.)\n\nOriginal error: {msg}"
                ) from exc
            raise
