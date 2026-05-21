"""Streamlit chat UI for the ThaBytePay Policy Assistant.

Talks to the FastAPI backend over HTTP. The UI never imports the rag package
directly — it's a pure consumer of the /chat endpoint.

Run with:
    streamlit run ui/app.py

Requires the API server to be running at API_BASE_URL (default localhost:8000).
"""
from __future__ import annotations

import os

import httpx
import streamlit as st


API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
REQUEST_TIMEOUT_SECONDS = 30.0


# ── Page setup ──────────────────────────────────────────────────────────

st.set_page_config(
    page_title="ThaBytePay Policy Assistant",
    page_icon="📘",
    layout="wide",
)


# ── Session state ───────────────────────────────────────────────────────

if "messages" not in st.session_state:
    st.session_state.messages = []


# ── Sidebar ─────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### About")
    st.markdown(
        "Ask questions about ThaBytePay's company policies. "
        "Answers are grounded in twelve internal policy documents and every claim is cited."
    )
    st.markdown("---")
    st.markdown("### Sample questions")
    samples = [
        "What is the daily transaction limit for a Tier-3 agent?",
        "How often are POS PIN encryption keys rotated?",
        "When must a stolen card be reported?",
        "What approval is needed to spend 800,000 KES?",
        "What is the RTO for mobile banking?",
        "What does the code of conduct say about gifts?",
    ]
    def _queue_sample(text: str) -> None:
        st.session_state.pending_question = text

    for q in samples:
        st.button(
            q,
            key=f"sample-{q}",
            use_container_width=True,
            on_click=_queue_sample,
            args=(q,),
        )
    st.markdown("---")
    st.markdown("### API")
    st.code(API_BASE_URL, language=None)
    st.markdown(f"[Open API docs]({API_BASE_URL}/docs)")
    st.markdown("---")
    def _clear_conversation() -> None:
        st.session_state.messages = []

    st.button(
        "Clear conversation",
        use_container_width=True,
        on_click=_clear_conversation,
    )


# ── Main header ─────────────────────────────────────────────────────────

st.title("ThaBytePay Policy Assistant")
st.caption(
    "Retrieval-augmented Q&A over ThaBytePay company policies. "
    "Powered by LangChain, Chroma, HuggingFace embeddings, and Groq Llama 3.3 70B."
)


# ── Render existing chat history ────────────────────────────────────────

def _render_assistant_message(msg: dict) -> None:
    """Render an assistant turn with its citations and latency."""
    meta = msg.get("meta") or {}
    out_of_corpus = meta.get("out_of_corpus", False)

    if out_of_corpus:
        st.warning(msg["content"], icon="🚫")
    else:
        st.markdown(msg["content"])

    citations = meta.get("citations") or []
    snippets = {s["source_idx"]: s["snippet"] for s in (meta.get("snippets") or [])}

    if citations:
        with st.expander(f"Sources ({len(citations)})", expanded=False):
            for c in citations:
                idx = c["source_idx"]
                st.markdown(
                    f"**[Source {idx}]** `{c['doc_id']}` — {c['doc_title']}  \n"
                    f"_Section:_ {c['section']}"
                )
                snippet = snippets.get(idx)
                if snippet:
                    st.markdown(f"> {snippet}")
                st.markdown("")

    total = meta.get("total_ms")
    retrieve = meta.get("retrieve_ms")
    generate = meta.get("generate_ms")
    if total is not None:
        st.caption(
            f"retrieve {retrieve:.0f}ms · generate {generate:.0f}ms · "
            f"total {total:.0f}ms"
        )


for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant":
            _render_assistant_message(msg)
        else:
            st.markdown(msg["content"])


# ── Backend call helpers ────────────────────────────────────────────────

def call_api(question: str) -> tuple[dict | None, str | None]:
    """Call the /chat endpoint. Returns (payload, error_message)."""
    try:
        resp = httpx.post(
            f"{API_BASE_URL}/chat",
            json={"question": question},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except httpx.ConnectError:
        return None, (
            "Cannot reach the API server. Make sure FastAPI is running at "
            f"`{API_BASE_URL}`."
        )
    except httpx.ReadTimeout:
        return None, "The request timed out. Try a shorter question or retry."
    except Exception as exc:
        return None, f"Unexpected error contacting the API: {exc}"

    if resp.status_code == 503:
        return None, "The service is still warming up. Please retry in a moment."
    if resp.status_code == 422:
        return None, "Your question must be between 1 and 1000 characters."
    if resp.status_code >= 500:
        return None, "The server hit an internal error. Please retry."
    if resp.status_code != 200:
        return None, f"Unexpected response from API: HTTP {resp.status_code}."

    try:
        return resp.json(), None
    except ValueError:
        return None, "Received an invalid response from the API."


# ── Input handling ──────────────────────────────────────────────────────

# Either the user typed something or they clicked a sample question
pending = st.session_state.pop("pending_question", None)
typed = st.chat_input("Ask about a ThaBytePay policy...")
question = pending or typed

if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            payload, error = call_api(question)

        if error:
            st.error(error)
            # Roll back the user message so they can retry cleanly
            st.session_state.messages.pop()
        else:
            assistant_msg = {
                "role": "assistant",
                "content": payload["answer"],
                "meta": payload,
            }
            st.session_state.messages.append(assistant_msg)
            _render_assistant_message(assistant_msg)
