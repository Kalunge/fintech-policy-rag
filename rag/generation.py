"""LLM client factory."""
from langchain_groq import ChatGroq

from rag.config import GROQ_API_KEY, LLM_MODEL
from rag.llm_cache import maybe_install_cache


def get_llm(
    temperature: float = 0.1,
    max_tokens: int = 500,
    disable_streaming: bool = False,
) -> ChatGroq:
    """Return a configured Groq chat client.

    Low temperature keeps the model close to the retrieved context (grounded).
    max_tokens caps the output length and worst-case latency.
    disable_streaming=True is required for tool-calling agents on Groq —
    Groq raises 'Failed to call a function' when streaming responses don't
    include a tool call.
    """
    if not GROQ_API_KEY:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Add it to .env or your environment."
        )

    # Optional dev-only LLM response cache. No-op in production.
    maybe_install_cache()

    return ChatGroq(
        model=LLM_MODEL,
        api_key=GROQ_API_KEY,
        temperature=temperature,
        max_tokens=max_tokens,
        disable_streaming=disable_streaming,
    )
