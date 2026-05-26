"""Optional SQLite-backed cache for LLM responses.

Enables free re-runs during dev iteration: when LLM_CACHE=1 is set in the
environment, identical prompts return cached responses without calling Groq.
Saves daily token budget while iterating.

Trade-offs and gotchas:

- Cache is keyed on the full prompt (system + history + user). Any change
  to the system prompt, retrieved context, or temperature produces a fresh
  call. This is correct behaviour, but means cache hits are rare while
  actively editing prompts.
- For agent loops, intermediate LLM calls are also cached. Most of the time
  this is fine; in rare cases it can lead to subtly stale traces if the
  agent state diverges from a previous run with the same prompt prefix.
- The cache file `.llm_cache.db` is gitignored — it's a local dev artifact,
  not part of the project state.

In production (Render), LLM_CACHE is unset and no caching occurs. Cached
test runs in CI are also avoided so that real failures aren't masked.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

log = logging.getLogger("llm_cache")

_CACHE_FILE = Path(__file__).resolve().parent.parent / ".llm_cache.db"
_INSTALLED = False


def maybe_install_cache() -> None:
    """Install the SQLite LLM cache if LLM_CACHE is set in the environment.

    Idempotent: safe to call multiple times. Subsequent calls are no-ops.
    """
    global _INSTALLED
    if _INSTALLED:
        return
    if os.getenv("LLM_CACHE", "").lower() not in ("1", "true", "yes", "on"):
        return

    try:
        from langchain_community.cache import SQLiteCache
        from langchain_core.globals import set_llm_cache
    except ImportError:
        log.warning("langchain_community is not installed; LLM cache disabled.")
        return

    set_llm_cache(SQLiteCache(database_path=str(_CACHE_FILE)))
    _INSTALLED = True
    log.info("LLM cache enabled at %s", _CACHE_FILE)
