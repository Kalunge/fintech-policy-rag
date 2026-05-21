"""LLM client factory."""
from langchain_groq import ChatGroq

from rag.config import GROQ_API_KEY, LLM_MODEL


def get_llm(temperature: float = 0.1, max_tokens: int = 500) -> ChatGroq:
    """Return a configured Groq chat client.

    Low temperature keeps the model close to the retrieved context (grounded).
    max_tokens caps the output length and worst-case latency.
    """
    if not GROQ_API_KEY:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Add it to .env or your environment."
        )

    return ChatGroq(
        model=LLM_MODEL,
        api_key=GROQ_API_KEY,
        temperature=temperature,
        max_tokens=max_tokens,
    )
