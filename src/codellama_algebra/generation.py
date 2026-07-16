"""Deterministic generation with raw-attempt preservation and one optional repair."""

from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any

from .model import LoadedModel
from .prompts import REPAIR_PROMPT_VERSION, build_repair_prompt, render_prompt
from .validation import ValidationResult, validate_response


@dataclass(frozen=True)
class GenerationConfig:
    """Generation parameters; sampling is disabled by default."""

    max_input_tokens: int = 2048
    max_new_tokens: int = 768
    deterministic: bool = True
    allow_repair: bool = True

    def __post_init__(self) -> None:
        if self.max_input_tokens < 1:
            raise ValueError("max_input_tokens must be positive")
        if self.max_new_tokens < 1:
            raise ValueError("max_new_tokens must be positive")


@dataclass(frozen=True)
class GenerationAttempt:
    """One model response and its complete validation result."""

    raw_response: str
    validation: ValidationResult
    duration_seconds: float


@dataclass(frozen=True)
class GenerationResult:
    """Structured generation result retaining every raw response."""

    prompt: str
    attempts: tuple[GenerationAttempt, ...]
    raw_response: str
    extracted_code: str | None
    validation: ValidationResult
    repair_used: bool
    repair_prompt_version: str | None


def generate_raw(
    tokenizer: Any,
    model: Any,
    prompt: str,
    config: GenerationConfig,
) -> str:
    """Generate text only; this function never validates or executes code."""

    inputs = tokenizer(
        prompt,
        return_tensors="pt",
        padding=True,
        truncation=True,
        max_length=config.max_input_tokens,
    )
    if hasattr(inputs, "to"):
        inputs = inputs.to(model.device)
    else:
        inputs = {key: value.to(model.device) for key, value in inputs.items()}
    kwargs = {
        "max_new_tokens": config.max_new_tokens,
        "do_sample": not config.deterministic,
        "eos_token_id": tokenizer.eos_token_id,
        "pad_token_id": tokenizer.pad_token_id,
        "use_cache": True,
    }
    output = model.generate(**inputs, **kwargs)
    prompt_length = inputs["input_ids"].shape[-1]
    new_tokens = output[0, prompt_length:]
    return tokenizer.decode(new_tokens, skip_special_tokens=True).strip()


def generate_problem(
    loaded: LoadedModel,
    problem: str,
    config: GenerationConfig | None = None,
) -> GenerationResult:
    """Generate and validate, with at most one format-repair attempt."""

    config = config or GenerationConfig()
    prompt = render_prompt(loaded.tokenizer, problem)
    started = time.perf_counter()
    first_raw = generate_raw(loaded.tokenizer, loaded.model, prompt, config)
    first_duration = time.perf_counter() - started
    first_validation = validate_response(first_raw)
    attempts = [GenerationAttempt(first_raw, first_validation, first_duration)]
    final_raw = first_raw
    final_validation = first_validation
    repair_used = False

    if not first_validation.valid and config.allow_repair:
        repair_used = True
        repair_prompt = build_repair_prompt(prompt, first_raw)
        started = time.perf_counter()
        final_raw = generate_raw(loaded.tokenizer, loaded.model, repair_prompt, config)
        repair_duration = time.perf_counter() - started
        final_validation = validate_response(final_raw)
        attempts.append(GenerationAttempt(final_raw, final_validation, repair_duration))

    return GenerationResult(
        prompt=prompt,
        attempts=tuple(attempts),
        raw_response=final_raw,
        extracted_code=final_validation.code,
        validation=final_validation,
        repair_used=repair_used,
        repair_prompt_version=REPAIR_PROMPT_VERSION if repair_used else None,
    )
