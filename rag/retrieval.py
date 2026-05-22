"""Top-k similarity retrieval over the persisted Chroma collection."""
from __future__ import annotations

from langchain_core.documents import Document

from rag.config import TOP_K
from rag.ingestion import load_vectorstore


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
        return self.vectorstore.similarity_search_with_score(query, k=k)
