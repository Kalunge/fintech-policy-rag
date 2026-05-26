"""Pytest configuration shared by all tests.

Adds a `--live` flag that opts into tests marked `@pytest.mark.live`. By
default, live tests are skipped to protect the Groq daily token quota
during local iteration. CI runs `pytest --live` to exercise the real
end-to-end paths.
"""
from __future__ import annotations

import pytest


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
