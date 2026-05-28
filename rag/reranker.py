"""Cross-encoder re-ranking for second-stage retrieval.

The bi-encoder retrieval in `rag/retrieval.py` is fast but coarse — it
embeds query and documents independently and so can't reason about them
together. A cross-encoder scores each (query, document) pair jointly,
producing a much more accurate relevance signal at the cost of running
the model once per candidate.

Two implementations:
- 'cohere': Cohere's hosted rerank-english-v3.0. Default for production
  because the deploy image stays lean (no torch). 150-300ms per call.
- 'local': cross-encoder/ms-marco-MiniLM-L-6-v2 via sentence-transformers.
  Free, no API key, but needs torch installed (requirements-local.txt).
  500-2000ms per call on CPU.

`get_reranker()` returns None when RERANKER_BACKEND='none' so callers
can use `if reranker:` to skip the stage entirely with no overhead.

See docs/15-reranking-deep-dive.md for the bi-encoder vs cross-encoder
distinction and the two-stage retrieval pattern.
"""
from __future__ import annotations

from typing import Protocol

from langchain_core.documents import Document

from rag.config import (
    COHERE_API_KEY,
    COHERE_RERANK_MODEL,
    LOCAL_RERANK_MODEL,
    RERANKER_BACKEND,
)


class Reranker(Protocol):
    """Common interface: take a query and a list of candidate (doc, distance)
    pairs from the bi-encoder; return them re-ordered by reranker score and
    truncated to top_k. The first-stage distance is preserved on the way
    through so the caller's guardrail logic still works.
    """

    def rerank(
        self,
        query: str,
        candidates: list[tuple[Document, float]],
        top_k: int,
    ) -> list[tuple[Document, float]]: ...


def get_reranker() -> Reranker | None:
    """Build a reranker according to RERANKER_BACKEND, or None to skip.

    Returning None instead of a no-op reranker keeps the retriever code
    simple — the call site does `if reranker: candidates = reranker.rerank(...)`
    and pays zero overhead when reranking is off.
    """
    if RERANKER_BACKEND == "cohere":
        return _CohereReranker()
    if RERANKER_BACKEND == "local":
        return _LocalReranker()
    if RERANKER_BACKEND in ("", "none"):
        return None
    raise ValueError(
        f"RERANKER_BACKEND must be 'cohere', 'local', or 'none' "
        f"(got {RERANKER_BACKEND!r})."
    )


class _CohereReranker:
    """Hosted cross-encoder via Cohere's rerank API."""

    def __init__(self) -> None:
        if not COHERE_API_KEY:
            raise RuntimeError(
                "RERANKER_BACKEND=cohere requires COHERE_API_KEY in the environment. "
                "Get a free trial key at https://dashboard.cohere.com/api-keys"
            )
        # Lazy import so installs without langchain_cohere still load this module.
        import cohere

        self._client = cohere.Client(api_key=COHERE_API_KEY)
        self._model = COHERE_RERANK_MODEL

    def rerank(
        self,
        query: str,
        candidates: list[tuple[Document, float]],
        top_k: int,
    ) -> list[tuple[Document, float]]:
        if not candidates:
            return []

        docs = [doc.page_content for doc, _ in candidates]
        response = self._client.rerank(
            model=self._model,
            query=query,
            documents=docs,
            top_n=min(top_k, len(candidates)),
        )

        reranked: list[tuple[Document, float]] = []
        for result in response.results:
            doc, original_distance = candidates[result.index]
            # Keep the bi-encoder distance so downstream guardrails still work.
            # The reranker score is available via result.relevance_score if
            # ever needed, but we don't currently propagate it.
            reranked.append((doc, original_distance))
        return reranked


class _LocalReranker:
    """Local cross-encoder via sentence-transformers.

    Requires the optional `requirements-local.txt` deps (torch + sentence-
    transformers). Slow on CPU; meant for offline iteration, not production.
    """

    def __init__(self) -> None:
        # Lazy import — never run on installs without torch.
        try:
            from sentence_transformers import CrossEncoder
        except ImportError as exc:
            raise RuntimeError(
                "RERANKER_BACKEND=local requires sentence-transformers. "
                "Install requirements-local.txt for offline reranker support."
            ) from exc

        self._model = CrossEncoder(LOCAL_RERANK_MODEL)

    def rerank(
        self,
        query: str,
        candidates: list[tuple[Document, float]],
        top_k: int,
    ) -> list[tuple[Document, float]]:
        if not candidates:
            return []

        pairs = [(query, doc.page_content) for doc, _ in candidates]
        scores = self._model.predict(pairs)
        # Sort candidates by score, descending. Use the original (doc, distance)
        # pair so the bi-encoder distance flows through unchanged.
        ranked = sorted(
            zip(candidates, scores), key=lambda x: float(x[1]), reverse=True
        )
        return [pair for pair, _ in ranked[:top_k]]
