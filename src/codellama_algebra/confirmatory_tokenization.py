"""Exact, no-truncation model-input tokenization for the confirmatory protocol."""

from __future__ import annotations

import hashlib
from typing import Any, Iterable

from .confirmatory import render_confirmatory_prompt, serialize_generated_token_ids

INPUT_TOKENIZER_ARGUMENTS = {
    "add_special_tokens": False,
    "padding": False,
    "truncation": False,
    "return_attention_mask": False,
    "return_token_type_ids": False,
}


def tokenize_rendered_prompt(
    tokenizer: Any,
    rendered_prompt: str,
    *,
    max_input_tokens: int = 2048,
) -> list[int]:
    """Tokenize the exact rendered prompt without adding tokens or truncating text."""

    encoded = tokenizer(rendered_prompt, **INPUT_TOKENIZER_ARGUMENTS)
    token_ids = encoded["input_ids"]
    if token_ids and isinstance(token_ids[0], list):
        if len(token_ids) != 1:
            raise ValueError("confirmatory tokenization accepts exactly one rendered prompt")
        token_ids = token_ids[0]
    values = [int(token_id) for token_id in token_ids]
    if not values:
        raise ValueError("rendered confirmatory prompt produced no input tokens")
    if len(values) > max_input_tokens:
        raise ValueError(
            f"confirmatory prompt has {len(values)} input tokens; limit is {max_input_tokens}; "
            "silent truncation is prohibited"
        )
    return values


def build_confirmatory_model_input(
    tokenizer: Any,
    problem: str,
    *,
    max_input_tokens: int = 2048,
) -> tuple[str, list[int]]:
    """Render and tokenize one frozen prompt through the exact confirmatory input path."""

    rendered = render_confirmatory_prompt(tokenizer, problem)
    return rendered, tokenize_rendered_prompt(
        tokenizer,
        rendered,
        max_input_tokens=max_input_tokens,
    )


def serialize_input_token_ids(token_ids: Iterable[int]) -> bytes:
    """Return the frozen compact ASCII JSON representation of prompt input IDs."""

    return serialize_generated_token_ids(token_ids)


def hash_input_token_ids(token_ids: Iterable[int]) -> str:
    """SHA-256 the frozen input-token serialization."""

    return hashlib.sha256(serialize_input_token_ids(token_ids)).hexdigest()
