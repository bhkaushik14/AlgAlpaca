"""Confirmatory execution entry point using the frozen future static policy."""

from __future__ import annotations

from dataclasses import replace

from .confirmatory_validation import validate_confirmatory_code
from .sandbox import ExecutionLimits, ExecutionResult, _execute_approved_code, _policy_failure
from .validation import ValidationResult


def execute_confirmatory_validated(
    validation: ValidationResult,
    limits: ExecutionLimits | None = None,
) -> ExecutionResult:
    """Recheck exact extracted source and execute it without altering its stdout contract."""

    if validation.valid and validation.code is not None:
        validation = validate_confirmatory_code(validation.code)
    if not validation.valid or validation.code is None:
        return _policy_failure(validation)
    result = _execute_approved_code(
        validation.code,
        limits or ExecutionLimits(),
        enforce_answer_contract=False,
    )
    return replace(result, validation=validation)
