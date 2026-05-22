"""Scoring functions for RAG evaluation.

Four classes of score:

1. LLM-as-judge groundedness — does every claim follow from the cited chunks?
2. LLM-as-judge citation accuracy — do the cited sources actually back the claims?
3. Deterministic correct-policy citation — does the answer cite the expected doc_id?
4. Deterministic partial fact coverage — do the must_contain facts appear in the answer?
5. Deterministic refusal — for out-of-corpus, does the answer match the refusal template?

LLM-as-judge uses the same Groq model as generation. Same-model judging has
known biases (positivity, length, self-preference). We mitigate with explicit
chunk-supporting prompts but document the limitation in the design doc.
"""
from __future__ import annotations

import json
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from rag.generation import get_llm
from rag.prompting import REFUSAL_TEMPLATE


JUDGE_SYSTEM_PROMPT = """You are a strict evaluator for a retrieval-augmented Q&A system.

You will be given a user QUESTION, the model's ANSWER, and the SOURCES the model
was shown. Score the answer on two dimensions and return a single JSON object.

Definitions:
- GROUNDED: every factual claim in the ANSWER is supported by at least one
  SOURCE. Restating a fact from a source counts. Inferring a number that is
  not in any source does not count. If the ANSWER is the refusal template,
  return grounded=true (refusal is by definition grounded).
- CITATIONS_ACCURATE: every [Source N] reference in the ANSWER points to a
  source whose content actually contains the cited claim. If the ANSWER has
  no citations and no claims, return citations_accurate=true. If the ANSWER
  cites a source that does not support the surrounding claim, return false.

Be strict. If you cannot find supporting text in the sources, score false.

Return ONLY a JSON object with this exact shape and nothing else:

{
  "grounded": true|false,
  "grounded_reasoning": "one sentence",
  "citations_accurate": true|false,
  "citations_reasoning": "one sentence"
}
"""


JUDGE_USER_TEMPLATE = """QUESTION:
{question}

ANSWER:
{answer}

SOURCES:
{sources}

Return your JSON evaluation now."""


def _format_sources(citations: list[dict], snippets: list[dict]) -> str:
    """Render the cited chunks for the judge's eyes."""
    if not citations:
        return "(no sources cited)"
    snip_by_idx = {s["source_idx"]: s["snippet"] for s in snippets}
    parts = []
    for c in citations:
        idx = c["source_idx"]
        snip = snip_by_idx.get(idx, "(snippet missing)")
        parts.append(
            f"[Source {idx}] {c['doc_title']} ({c['doc_id']}) — {c['section']}\n{snip}"
        )
    return "\n\n".join(parts)


def _parse_judge_json(text: str) -> dict[str, Any]:
    """Pull the first JSON object out of the LLM's response."""
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object in judge response: {text[:200]}")
    return json.loads(match.group(0))


def judge(
    question: str,
    answer: str,
    citations: list[dict],
    snippets: list[dict],
    judge_llm=None,
) -> dict[str, Any]:
    """Use an LLM to score groundedness and citation accuracy."""
    judge_llm = judge_llm or get_llm(temperature=0.0, max_tokens=400)
    messages = [
        SystemMessage(content=JUDGE_SYSTEM_PROMPT),
        HumanMessage(
            content=JUDGE_USER_TEMPLATE.format(
                question=question,
                answer=answer,
                sources=_format_sources(citations, snippets),
            )
        ),
    ]
    response = judge_llm.invoke(messages)
    return _parse_judge_json(response.content)


def correct_policy_cited(
    citations: list[dict], expected_doc_id: str | None
) -> bool:
    """Whether any cited source has the expected document ID."""
    if not expected_doc_id:
        return True
    return any(c.get("doc_id") == expected_doc_id for c in citations)


def partial_match(answer: str, must_contain: list[str] | None) -> dict:
    """Fraction of required strings that appear (case-insensitive) in the answer."""
    if not must_contain:
        return {"score": 1.0, "missing": []}
    answer_lower = answer.lower()
    missing = [s for s in must_contain if s.lower() not in answer_lower]
    score = (len(must_contain) - len(missing)) / len(must_contain)
    return {"score": score, "missing": missing}


def correct_refusal(answer: str) -> bool:
    """For out-of-corpus questions, did the model return the refusal template?"""
    return REFUSAL_TEMPLATE.lower() in answer.lower()
