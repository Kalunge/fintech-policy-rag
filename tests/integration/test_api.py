"""Integration tests for the FastAPI endpoints."""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from api.main import app


def _collect_sse_events(client: TestClient, payload: dict) -> list[dict]:
    """POST to /chat/stream and parse the SSE response into a list of events."""
    events: list[dict] = []
    with client.stream("POST", "/chat/stream", json=payload) as resp:
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")
        for line in resp.iter_lines():
            if not line.startswith("data: "):
                continue
            events.append(json.loads(line[len("data: "):]))
    return events


@pytest.fixture(scope="module")
def client():
    # `with TestClient(...)` triggers FastAPI lifespan, so the pipeline warms up.
    with TestClient(app) as c:
        yield c


def test_health_returns_200(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200


def test_health_payload_shape(client: TestClient) -> None:
    data = client.get("/health").json()
    assert data["status"] == "healthy"
    assert data["ready"] is True
    assert data["model"]  # non-empty string when ready


def test_root_returns_html(client: TestClient) -> None:
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "ThaBytePay" in resp.text


def test_chat_rejects_missing_question(client: TestClient) -> None:
    resp = client.post("/chat", json={})
    assert resp.status_code == 422


def test_chat_rejects_empty_question(client: TestClient) -> None:
    resp = client.post("/chat", json={"question": ""})
    assert resp.status_code == 422


@pytest.mark.live
def test_chat_returns_grounded_answer(client: TestClient) -> None:
    resp = client.post(
        "/chat",
        json={"question": "What is the daily transaction limit for a Tier-3 agent?"},
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["out_of_corpus"] is False
    assert isinstance(data["answer"], str) and len(data["answer"]) > 0
    assert len(data["citations"]) >= 1
    assert data["citations"][0]["doc_id"].startswith("TBP-POL-")
    assert data["total_ms"] > 0


@pytest.mark.live
def test_chat_out_of_corpus_refusal(client: TestClient) -> None:
    resp = client.post(
        "/chat",
        json={"question": "What is the best recipe for banana bread?"},
    )
    assert resp.status_code == 200
    data = resp.json()
    # Either the in-prompt refusal or the distance guardrail must have triggered.
    assert "can only answer questions about ThaBytePay policies" in data["answer"]


def test_chat_stream_rejects_empty_question(client: TestClient) -> None:
    resp = client.post("/chat/stream", json={"question": ""})
    assert resp.status_code == 422


@pytest.mark.live
def test_chat_stream_yields_tokens_then_done(client: TestClient) -> None:
    events = _collect_sse_events(
        client,
        {"question": "What is the daily transaction limit for a Tier-3 agent?"},
    )

    # At least one token event then exactly one done event at the end.
    token_events = [e for e in events if "token" in e]
    done_events = [e for e in events if e.get("done")]
    assert len(token_events) >= 1
    assert len(done_events) == 1
    assert events[-1] is done_events[0]

    done = done_events[0]
    assert done["out_of_corpus"] is False
    assert isinstance(done["answer"], str) and len(done["answer"]) > 0
    assert len(done["citations"]) >= 1
    assert done["total_ms"] > 0

    # Public shape: internal-only fields must not leak through /chat/stream.
    assert "full_chunks" not in done
    assert "retrieval_debug" not in done


@pytest.mark.live
def test_chat_stream_out_of_corpus(client: TestClient) -> None:
    events = _collect_sse_events(
        client,
        {"question": "What is the best recipe for banana bread?"},
    )

    token_events = [e for e in events if "token" in e]
    done_events = [e for e in events if e.get("done")]
    assert len(token_events) >= 1
    assert len(done_events) == 1

    # Two valid refusal paths: the distance guard fires (out_of_corpus=true,
    # no LLM call) or the LLM refuses via its system prompt. We assert on the
    # user-visible contract — that the refusal text is streamed — rather than
    # on which guard tripped, since that depends on embedding model + corpus.
    refusal_text = "".join(e["token"] for e in token_events)
    assert "can only answer questions about ThaBytePay policies" in refusal_text
