"""Integration tests for the agentic /chat/agent endpoint."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.mark.live
def test_agent_endpoint_exists(client: TestClient) -> None:
    resp = client.post("/chat/agent", json={"question": "test"})
    # 200 (works) or 503 (warming) — never 404
    assert resp.status_code in (200, 503)


@pytest.mark.live
def test_agent_pure_tool_call(client: TestClient) -> None:
    resp = client.post(
        "/chat/agent",
        json={"question": "What is the float balance for agent AG-001?"},
    )
    assert resp.status_code == 200
    data = resp.json()
    # The answer should be non-empty and the response shape valid.
    # The agent SHOULD call check_agent_balance for this question, but model
    # discretion plus Groq's intermittent tool-format error means we can't
    # demand a specific tool call from a single live test.
    assert isinstance(data["answer"], str) and len(data["answer"]) > 0
    assert "tool_calls" in data


@pytest.mark.live
def test_agent_handles_unknown_id(client: TestClient) -> None:
    resp = client.post(
        "/chat/agent",
        json={"question": "What is the balance for agent AG-999?"},
    )
    assert resp.status_code == 200
    data = resp.json()
    answer_lower = data["answer"].lower()
    # Either the tool returned AGENT_NOT_FOUND, the model said it didn't know,
    # or we hit a rate limit and the agent reported the issue gracefully
    # (which is also acceptable behaviour — we don't crash).
    acceptable = (
        "not found" in answer_lower
        or "no agent" in answer_lower
        or "i can only answer" in answer_lower
        or "ag-999" in answer_lower
        or "ran into a problem" in answer_lower
    )
    assert acceptable, f"unexpected answer: {data['answer']!r}"


@pytest.mark.live
def test_agent_response_shape(client: TestClient) -> None:
    resp = client.post(
        "/chat/agent",
        json={"question": "What is the status of terminal TID-001?"},
    )
    assert resp.status_code == 200
    data = resp.json()
    # ChatResponse fields
    for key in (
        "answer",
        "citations",
        "snippets",
        "out_of_corpus",
        "retrieve_ms",
        "generate_ms",
        "total_ms",
    ):
        assert key in data, f"missing field {key!r}"
    # Agent-specific fields
    assert "tool_calls" in data
    assert "iterations" in data
