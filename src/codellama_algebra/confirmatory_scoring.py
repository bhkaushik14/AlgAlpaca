"""Future-only scoring entry point with narrow canonical set-name corrections."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from .scoring import ExpectedAnswer, ScoreResult, score_answer

_CANONICAL_SET_NAMES = {
    "EmptySet": "FiniteSet()",
    "S.EmptySet": "FiniteSet()",
    "Reals": "Interval(-oo, oo)",
    "S.Reals": "Interval(-oo, oo)",
}


def _normalize_interval_constant(text: str) -> str:
    stripped = text.strip()
    return _CANONICAL_SET_NAMES.get(stripped, text)


def score_confirmatory_answer(
    actual: str,
    expected: ExpectedAnswer | dict[str, Any],
    timeout_seconds: float = 3.0,
) -> ScoreResult:
    """Delegate to Stage 2B scoring after exact-name set normalization only."""

    schema = (
        expected if isinstance(expected, ExpectedAnswer) else ExpectedAnswer.from_dict(expected)
    )
    if schema.kind == "interval_set":
        actual = _normalize_interval_constant(actual)
        schema = replace(schema, value=_normalize_interval_constant(str(schema.value)))
    return score_answer(actual, schema, timeout_seconds=timeout_seconds)
