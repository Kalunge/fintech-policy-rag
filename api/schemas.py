"""Request and response models for the API layer."""
from __future__ import annotations

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="The user's question. 1 to 1000 characters.",
    )


class Citation(BaseModel):
    source_idx: int
    doc_id: str
    doc_title: str
    section: str
    chunk_id: str


class Snippet(BaseModel):
    source_idx: int
    snippet: str


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation]
    snippets: list[Snippet]
    out_of_corpus: bool
    retrieve_ms: float
    generate_ms: float
    total_ms: float


class ToolCall(BaseModel):
    tool: str
    args: dict
    summary: str
    result: dict | str | None = None


class AgentChatResponse(ChatResponse):
    tool_calls: list[ToolCall] = []
    iterations: int = 0


class HealthResponse(BaseModel):
    status: str
    ready: bool
    model: str | None = None
