"""Pytest configuration shared by all tests.

Adds a `--live` flag that opts into tests marked `@pytest.mark.live`. By
default, live tests are skipped to protect the Groq daily token quota
during local iteration. CI runs `pytest --live` to exercise the real
end-to-end paths.
"""
from __future__ import annotations

import pytest
import httpx


# String the API uses in the 503 detail when Groq returns 429. Tests use
# skip_if_rate_limited() to convert these into pytest.skip rather than
# fail — the test code is fine, the upstream LLM is just throttling.
RATE_LIMIT_DETAIL_PREFIX = "Upstream LLM rate-limited"


def pytest_addoption(parser):
    parser.addoption(
        "--live",
        action="store_true",
        default=False,
        help="Run tests marked @pytest.mark.live (these hit real LLM APIs and consume quota).",
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--live"):
        return
    skip_live = pytest.mark.skip(
        reason="needs --live to run (skipped by default to protect LLM quota)"
    )
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip_live)


def skip_if_rate_limited(resp: httpx.Response) -> None:
    """If the API returned a 503 because Groq is throttling, skip the test
    instead of failing. Daily TPD caps are an upstream condition, not a
    regression in our code.
    """
    if resp.status_code == 503 and RATE_LIMIT_DETAIL_PREFIX in resp.text:
        pytest.skip(f"Upstream LLM rate-limited (status 503): {resp.text}")
