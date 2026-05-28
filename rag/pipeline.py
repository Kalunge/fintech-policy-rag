"""End-to-end RAG orchestration: question in, grounded answer out."""
from __future__ import annotations

import time
from typing import Any, Iterator

from langchain_core.documents import Document

from rag.generation import get_llm
from rag.guardrails import (
    enforce_length,
    extract_citation_indices,
    is_out_of_corpus,
)
from rag.prompting import REFUSAL_TEMPLATE, build_messages
from rag.retrieval import Retriever


SNIPPET_CHARS = 320


def _build_citation(doc: Document, source_idx: int) -> dict[str, Any]:
    meta = doc.metadata or {}
    return {
        "source_idx": source_idx,
        "doc_id": meta.get("doc_id", ""),
        "doc_title": meta.get("doc_title", ""),
        "section": meta.get("section", ""),
        "chunk_id": meta.get("chunk_id", ""),
    }


def _build_snippet(doc: Document, source_idx: int) -> dict[str, Any]:
    text = (doc.page_content or "").strip()
    snippet = text[:SNIPPET_CHARS]
    if len(text) > SNIPPET_CHARS:
        snippet = snippet.rstrip() + "..."
    return {"source_idx": source_idx, "snippet": snippet}


def _build_full_chunk(doc: Document, source_idx: int) -> dict[str, Any]:
    """Untruncated chunk content for the eval judge. Not exposed via the public API."""
    return {
        "source_idx": source_idx,
        "snippet": (doc.page_content or "").strip(),
    }


class RAGPipeline:
    """Single-call entry point for the assistant."""

    def __init__(self) -> None:
        self.retriever = Retriever()
        self.llm = get_llm()

    def answer(self, question: str) -> dict[str, Any]:
        t_start = time.time()

        # Stage 1: retrieve
        t_retrieve = time.time()
        retrieved = self.retriever.retrieve(question)
        retrieve_ms = (time.time() - t_retrieve) * 1000

        # Stage 2: out-of-corpus guard
        if is_out_of_corpus(retrieved):
            return {
                "answer": REFUSAL_TEMPLATE,
                "citations": [],
                "snippets": [],
                "full_chunks": [],
                "out_of_corpus": True,
                "retrieve_ms": round(retrieve_ms, 1),
                "generate_ms": 0.0,
                "total_ms": round((time.time() - t_start) * 1000, 1),
                "retrieval_debug": [
                    {
                        "source_idx": i + 1,
                        "doc_id": doc.metadata.get("doc_id", ""),
                        "section": doc.metadata.get("section", ""),
                        "distance": round(score, 4),
                    }
                    for i, (doc, score) in enumerate(retrieved)
                ],
            }

        docs = [doc for doc, _ in retrieved]

        # Stage 3: prompt and generate
        messages = build_messages(question, docs)
        t_generate = time.time()
        response = self.llm.invoke(messages)
        generate_ms = (time.time() - t_generate) * 1000
        answer_text = enforce_length(response.content)

        # Stage 4: extract citations and build snippets
        cited_indices = extract_citation_indices(answer_text)
        citations: list[dict[str, Any]] = []
        snippets: list[dict[str, Any]] = []
        full_chunks: list[dict[str, Any]] = []
        for idx in cited_indices:
            if 1 <= idx <= len(docs):
                citations.append(_build_citation(docs[idx - 1], idx))
                snippets.append(_build_snippet(docs[idx - 1], idx))
                full_chunks.append(_build_full_chunk(docs[idx - 1], idx))

        return {
            "answer": answer_text,
            "citations": citations,
            "snippets": snippets,
            "full_chunks": full_chunks,
            "out_of_corpus": False,
            "retrieve_ms": round(retrieve_ms, 1),
            "generate_ms": round(generate_ms, 1),
            "total_ms": round((time.time() - t_start) * 1000, 1),
            "retrieval_debug": [
                {
                    "source_idx": i + 1,
                    "doc_id": doc.metadata.get("doc_id", ""),
                    "section": doc.metadata.get("section", ""),
                    "distance": round(score, 4),
                }
                for i, (doc, score) in enumerate(retrieved)
            ],
        }

    def stream_answer(self, question: str) -> Iterator[dict[str, Any]]:
        """Stream the answer as the LLM generates it.

        Yields a sequence of dicts:
            {"token": "..."}      for each chunk the LLM emits
            {"done": True, ...}   once at the end, carrying the same metadata
                                  shape as answer() (citations, snippets,
                                  latency, out_of_corpus, retrieval_debug).

        Citations are extracted after streaming ends because they depend on
        the full answer text. The out-of-corpus refusal is deterministic and
        is emitted as one token followed by the done event.
        """
        t_start = time.time()

        t_retrieve = time.time()
        retrieved = self.retriever.retrieve(question)
        retrieve_ms = (time.time() - t_retrieve) * 1000

        retrieval_debug = [
            {
                "source_idx": i + 1,
                "doc_id": doc.metadata.get("doc_id", ""),
                "section": doc.metadata.get("section", ""),
                "distance": round(score, 4),
            }
            for i, (doc, score) in enumerate(retrieved)
        ]

        if is_out_of_corpus(retrieved):
            yield {"token": REFUSAL_TEMPLATE}
            yield {
                "done": True,
                "answer": REFUSAL_TEMPLATE,
                "citations": [],
                "snippets": [],
                "full_chunks": [],
                "out_of_corpus": True,
                "retrieve_ms": round(retrieve_ms, 1),
                "generate_ms": 0.0,
                "total_ms": round((time.time() - t_start) * 1000, 1),
                "retrieval_debug": retrieval_debug,
            }
            return

        docs = [doc for doc, _ in retrieved]
        messages = build_messages(question, docs)

        t_generate = time.time()
        chunks: list[str] = []
        for chunk in self.llm.stream(messages):
            text = chunk.content
            if text:
                chunks.append(text)
                yield {"token": text}
        generate_ms = (time.time() - t_generate) * 1000

        answer_text = enforce_length("".join(chunks))
        cited_indices = extract_citation_indices(answer_text)
        citations: list[dict[str, Any]] = []
        snippets: list[dict[str, Any]] = []
        full_chunks: list[dict[str, Any]] = []
        for idx in cited_indices:
            if 1 <= idx <= len(docs):
                citations.append(_build_citation(docs[idx - 1], idx))
                snippets.append(_build_snippet(docs[idx - 1], idx))
                full_chunks.append(_build_full_chunk(docs[idx - 1], idx))

        yield {
            "done": True,
            "answer": answer_text,
            "citations": citations,
            "snippets": snippets,
            "full_chunks": full_chunks,
            "out_of_corpus": False,
            "retrieve_ms": round(retrieve_ms, 1),
            "generate_ms": round(generate_ms, 1),
            "total_ms": round((time.time() - t_start) * 1000, 1),
            "retrieval_debug": retrieval_debug,
        }
