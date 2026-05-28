"""Streamlit chat UI for the ThaBytePay Policy Assistant.

Talks to the FastAPI backend over HTTP. The UI never imports the rag package
directly — it's a pure consumer of the /chat endpoint.

Run with:
    streamlit run ui/app.py

Requires the API server to be running at API_BASE_URL (default localhost:8000).
"""
from __future__ import annotations

import json
import os
from typing import Iterator

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
if "agent_mode" not in st.session_state:
    st.session_state.agent_mode = False


# ── Sidebar ─────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### About")
    st.markdown(
        "Ask questions about ThaBytePay's company policies. "
        "Answers are grounded in twelve internal policy documents and every claim is cited."
    )

    st.markdown("---")
    st.markdown("### Mode")
    st.session_state.agent_mode = st.toggle(
        "Agent mode (stretch)",
        value=st.session_state.agent_mode,
        help=(
            "Off: standard policy Q&A. "
            "On: the assistant can also call banking tools "
            "(agent balance, transaction lookup, terminal status, "
            "compliance scorecard, mock deposit)."
        ),
    )

    st.markdown("---")
    if st.session_state.agent_mode:
        st.markdown("### Sample questions (agent)")
        samples = [
            "What is the float balance for agent AG-001?",
            "Tell me about agent AG-008's compliance issues.",
            "Show me the details of transaction TXN-1006.",
            "What is the status of terminal TID-006?",
            "Simulate a deposit of 50,000 KES for agent AG-001 customer +254712345678.",
            "Per the policy, can agent AG-007 process a 60,000 KES deposit?",
        ]
    else:
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

def _render_tool_calls(meta: dict) -> None:
    tool_calls = meta.get("tool_calls") or []
    if not tool_calls:
        return
    with st.expander(f"Tool calls ({len(tool_calls)})", expanded=False):
        for tc in tool_calls:
            args_str = ", ".join(f"{k}={v!r}" for k, v in (tc.get("args") or {}).items())
            st.markdown(f"**`{tc['tool']}({args_str})`** — {tc.get('summary', '')}")
            result = tc.get("result")
            if isinstance(result, dict) and result.get("error"):
                st.markdown(f"_Error:_ `{result.get('code')}` — {result.get('message')}")
            elif isinstance(result, dict):
                st.json(result, expanded=False)


def _render_trailing_metadata(meta: dict) -> None:
    """Sources expander + latency caption. Reused by history rendering and by
    the streaming path (after `st.write_stream` finishes drawing the answer).
    """
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


def _render_assistant_message(msg: dict) -> None:
    """Render a historical assistant turn (tool calls, body, citations, latency)."""
    meta = msg.get("meta") or {}
    _render_tool_calls(meta)

    if meta.get("out_of_corpus"):
        st.warning(msg["content"], icon="🚫")
    else:
        st.markdown(msg["content"])

    _render_trailing_metadata(meta)


for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant":
            _render_assistant_message(msg)
        else:
            st.markdown(msg["content"])


# ── Backend call helpers ────────────────────────────────────────────────

def call_api(question: str, agent_mode: bool = False) -> tuple[dict | None, str | None]:
    """Call the /chat or /chat/agent endpoint. Returns (payload, error_message)."""
    endpoint = "/chat/agent" if agent_mode else "/chat"
    try:
        resp = httpx.post(
            f"{API_BASE_URL}{endpoint}",
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


def stream_api(question: str, meta: dict) -> Iterator[str]:
    """Consume /chat/stream and yield each token for `st.write_stream`.

    Side effect: populates `meta` with the done-event payload (and `error`
    if anything goes wrong). The caller reads `meta` after the stream
    finishes to render citations and latency.
    """
    try:
        with httpx.stream(
            "POST",
            f"{API_BASE_URL}/chat/stream",
            json={"question": question},
            timeout=httpx.Timeout(REQUEST_TIMEOUT_SECONDS),
        ) as resp:
            if resp.status_code == 503:
                meta["error"] = "The service is still warming up. Please retry in a moment."
                return
            if resp.status_code == 422:
                meta["error"] = "Your question must be between 1 and 1000 characters."
                return
            if resp.status_code != 200:
                meta["error"] = f"Unexpected response from API: HTTP {resp.status_code}."
                return

            for line in resp.iter_lines():
                if not line.startswith("data: "):
                    continue
                payload = json.loads(line[len("data: "):])
                if payload.get("done"):
                    meta.update(payload)
                elif "error" in payload:
                    meta["error"] = payload["error"]
                    return
                elif "token" in payload:
                    yield payload["token"]
    except httpx.ConnectError:
        meta["error"] = (
            "Cannot reach the API server. Make sure FastAPI is running at "
            f"`{API_BASE_URL}`."
        )
    except httpx.ReadTimeout:
        meta["error"] = "The request timed out. Try a shorter question or retry."
    except Exception as exc:
        meta["error"] = f"Unexpected error during streaming: {exc}"


# ── Input handling ──────────────────────────────────────────────────────

# Either the user typed something or they clicked a sample question
pending = st.session_state.pop("pending_question", None)
chat_placeholder = (
    "Ask about an agent, terminal, transaction, or policy..."
    if st.session_state.agent_mode
    else "Ask about a ThaBytePay policy..."
)
typed = st.chat_input(chat_placeholder)
question = pending or typed

if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        if st.session_state.agent_mode:
            # Agent flow stays synchronous — tool-calling loops don't map cleanly
            # to token streaming (see docs/14-streaming-deep-dive.md).
            with st.spinner("Looking up data and policies..."):
                payload, error = call_api(question, agent_mode=True)

            if error:
                st.error(error)
                st.session_state.messages.pop()
            else:
                assistant_msg = {
                    "role": "assistant",
                    "content": payload["answer"],
                    "meta": payload,
                }
                st.session_state.messages.append(assistant_msg)
                _render_assistant_message(assistant_msg)
        else:
            # RAG flow streams tokens via /chat/stream. write_stream renders
            # them with a typewriter effect; metadata arrives in the done event
            # and is rendered below as the Sources expander + latency caption.
            meta: dict = {}
            streamed_text = st.write_stream(stream_api(question, meta))

            if "error" in meta:
                st.error(meta["error"])
                st.session_state.messages.pop()
            else:
                _render_trailing_metadata(meta)
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": meta.get("answer") or streamed_text,
                        "meta": meta,
                    }
                )
