"""Prompt construction for the RAG pipeline."""
from __future__ import annotations

from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage


REFUSAL_TEMPLATE = (
    "I can only answer questions about ThaBytePay policies. "
    "The provided context does not cover this topic."
)


SYSTEM_PROMPT = """You are the ThaBytePay Policy Assistant.

Your role is to answer employee questions about company policies using ONLY the
policy excerpts provided in the context below.

Rules you MUST follow:
1. If the context does not contain enough information to answer the question,
   reply exactly: "{refusal}"
2. Cite every factual claim using the [Source N] format, where N corresponds
   to the source number in the context.
3. Keep your answer concise — under 200 words.
4. Do not invent facts that are not present in the context.
5. Quote specific numbers, timeframes, and policy IDs exactly as written.

Context:
{context}
"""


def build_context(retrieved: list[Document]) -> str:
    """Format retrieved chunks as numbered source blocks."""
    parts: list[str] = []
    for i, doc in enumerate(retrieved, start=1):
        meta = doc.metadata or {}
        title = meta.get("doc_title", "Unknown Document")
        doc_id = meta.get("doc_id", "")
        section = meta.get("section", "")
        header = f"[Source {i}] {title}"
        if doc_id:
            header += f" ({doc_id})"
        if section:
            header += f" — {section}"
        parts.append(f"{header}\n{doc.page_content.strip()}\n")
    return "\n".join(parts)


def build_messages(question: str, retrieved: list[Document]) -> list:
    """Compose the system and human messages for the LLM call."""
    system_content = SYSTEM_PROMPT.format(
        refusal=REFUSAL_TEMPLATE,
        context=build_context(retrieved),
    )
    return [
        SystemMessage(content=system_content),
        HumanMessage(content=question),
    ]
