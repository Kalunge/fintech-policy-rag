"""Guardrails around the RAG pipeline.

Three independent protections:
1. Pre-LLM out-of-corpus detection by similarity threshold.
2. Citation extraction so we can verify the answer is grounded.
3. Length enforcement as a belt-and-braces output cap.
"""
from __future__ import annotations

import re

from langchain_core.documents import Document


# Cosine distance threshold. Below this the chunk is considered relevant.
# Calibrated against the eval set in Phase 7; loose default for now.
OUT_OF_CORPUS_DISTANCE = 1.2

# Matches any "Source N" reference, regardless of bracket structure.
# Catches all of:  [Source 1]  [Source 1, Source 2]  (Source 1)  Source 1 and Source 2
CITATION_PATTERN = re.compile(r"Source\s+(\d+)", flags=re.IGNORECASE)


def is_out_of_corpus(retrieved_with_scores: list[tuple[Document, float]]) -> bool:
    """True if the best retrieved chunk is too dissimilar to the query."""
    if not retrieved_with_scores:
        return True
    best_distance = retrieved_with_scores[0][1]
    return best_distance > OUT_OF_CORPUS_DISTANCE


def extract_citation_indices(answer: str) -> list[int]:
    """Return sorted unique 1-based source numbers cited in the answer.

    Lenient: finds 'Source N' anywhere in the text, so multi-source brackets like
    [Source 1, Source 2] are captured correctly.
    """
    matches = CITATION_PATTERN.findall(answer)
    return sorted({int(m) for m in matches})


def has_citations(answer: str) -> bool:
    return len(extract_citation_indices(answer)) > 0


def enforce_length(answer: str, max_chars: int = 2000) -> str:
    if len(answer) > max_chars:
        return answer[: max_chars - 3] + "..."
    return answer
