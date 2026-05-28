"""Top-k similarity retrieval over the persisted Chroma collection."""
from __future__ import annotations

from langchain_core.documents import Document

from rag.config import EMBEDDING_BACKEND, RERANK_CANDIDATE_K, TOP_K
from rag.ingestion import load_vectorstore
from rag.reranker import Reranker, get_reranker


class EmbeddingDimensionMismatch(RuntimeError):
    """The Chroma index was built with a different embedding backend than
    the one currently configured. The user must either switch backends or
    rebuild the index."""


class Retriever:
    """Wraps the vector store to expose a simple top-k search interface.

    Returns chunks alongside their cosine distances so downstream
    guardrails can decide whether the question is in-scope.

    When a reranker is configured (RERANKER_BACKEND != 'none'), the
    retriever runs two-stage retrieval: it pulls RERANK_CANDIDATE_K
    candidates from Chroma, scores them with the cross-encoder, and
    returns the top-k. The bi-encoder distance is preserved on the
    returned pairs so the out-of-corpus guardrail still works.
    """

    def __init__(
        self,
        k: int = TOP_K,
        reranker: Reranker | None = None,
        candidate_k: int = RERANK_CANDIDATE_K,
    ):
        self.k = k
        self.candidate_k = candidate_k
        self.vectorstore = load_vectorstore()
        # Default to whatever RERANKER_BACKEND says; let callers override.
        self.reranker = reranker if reranker is not None else get_reranker()

    def retrieve(self, query: str, k: int | None = None) -> list[tuple[Document, float]]:
        """Return the top-k most similar chunks with their distance scores.

        Chroma reports distances where 0 = identical and ~2 = opposite for
        normalized cosine similarity.
        """
        k = k or self.k
        # If reranking is on, pull a wider candidate set so the cross-encoder
        # has something to actually re-order.
        first_stage_k = max(self.candidate_k, k) if self.reranker else k

        try:
            candidates = self.vectorstore.similarity_search_with_score(
                query, k=first_stage_k
            )
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

        if not self.reranker:
            return candidates

        return self.reranker.rerank(query, candidates, top_k=k)
