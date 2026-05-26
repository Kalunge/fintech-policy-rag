"""Integration tests for the FastAPI endpoints."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.main import app


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
