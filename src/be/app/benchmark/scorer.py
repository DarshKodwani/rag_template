"""Scoring functions for RAG benchmarks."""
from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.config import Settings

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Retrieval metrics
# ---------------------------------------------------------------------------


def retrieval_recall(
    retrieved_pages: list[int | None],
    expected_pages: list[int],
) -> float:
    """Fraction of expected source pages found in the retrieved chunks.

    Returns 1.0 if all expected pages were retrieved, 0.0 if none were.
    """
    if not expected_pages:
        return 1.0
    retrieved_set = {p for p in retrieved_pages if p is not None}
    expected_set = set(expected_pages)
    hits = retrieved_set & expected_set
    return len(hits) / len(expected_set)


def retrieval_precision(
    retrieved_pages: list[int | None],
    expected_pages: list[int],
) -> float:
    """Fraction of retrieved pages that are in the expected set."""
    retrieved_set = {p for p in retrieved_pages if p is not None}
    if not retrieved_set:
        return 0.0
    expected_set = set(expected_pages)
    hits = retrieved_set & expected_set
    return len(hits) / len(retrieved_set)


# ---------------------------------------------------------------------------
# LLM-as-judge
# ---------------------------------------------------------------------------

_JUDGE_SYSTEM = """You are an expert evaluator assessing the quality of a RAG system's answer.
You will be given a question, the expected (ground truth) answer, and the system's generated answer.

Score the generated answer on TWO dimensions, each from 0 to 5:

1. **Correctness**: Does the generated answer contain factually accurate information consistent with the expected answer? (0 = completely wrong, 5 = fully correct)
2. **Completeness**: Does the generated answer cover all the key points in the expected answer? (0 = misses everything, 5 = covers all points)

Respond ONLY with valid JSON (no markdown fences):
{"correctness": <int 0-5>, "completeness": <int 0-5>, "explanation": "<brief reason>"}"""

_JUDGE_USER = """Question: {question}

Expected answer: {expected_answer}

Generated answer: {generated_answer}"""


def llm_judge(
    question: str,
    expected_answer: str,
    generated_answer: str,
    settings: "Settings",
) -> dict:
    """Use an LLM to score the generated answer against ground truth.

    Returns dict with keys: correctness (0-5), completeness (0-5), explanation.
    """
    from app.rag.search import _get_client

    client = _get_client(settings)
    model = (
        settings.azure_openai_chat_deployment
        if settings.azure_keys_present
        else settings.openai_chat_model
    )

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": _JUDGE_SYSTEM},
            {
                "role": "user",
                "content": _JUDGE_USER.format(
                    question=question,
                    expected_answer=expected_answer,
                    generated_answer=generated_answer,
                ),
            },
        ],
        temperature=0.0,
    )
    text = response.choices[0].message.content or "{}"
    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        log.warning("LLM judge returned invalid JSON: %s", text)
        result = {"correctness": 0, "completeness": 0, "explanation": f"Parse error: {text}"}

    return {
        "correctness": int(result.get("correctness", 0)),
        "completeness": int(result.get("completeness", 0)),
        "explanation": result.get("explanation", ""),
    }
