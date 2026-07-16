"""Frozen, generation-free configuration helpers for the Stage 3 confirmatory run."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable

PROMPT_VERSION = "confirmatory-algebra-to-code-v2"
ORDER_SEED = 20260714

SYSTEM_PROMPT = "You write complete executable Python programs that solve algebra problems."

USER_PROMPT_TEMPLATE = """Write one complete executable Python program that solves the algebra problem below.

Use SymPy when useful. The program must print its final mathematical answer to standard output. You may use either one line beginning with `ANSWER:` or one unambiguous mathematical output line. Do not provide a prose-only solution or any explanation outside the program.

Algebra problem:
{problem}
"""

FROZEN_GENERATION_CONFIG = {
    "base_model_id": "codellama/CodeLlama-7b-Instruct-hf",
    "base_model_revision": "22cb240e0292b0b5ab4c17ccd97aa3a2f799cbed",
    "tokenizer_id": "codellama/CodeLlama-7b-Instruct-hf",
    "tokenizer_revision": "22cb240e0292b0b5ab4c17ccd97aa3a2f799cbed",
    "adapter_label": "algebra-qlora-adapter",
    "adapter_sha256": "4dfc1a875feccfdb7affd98326d63704b5cf0ec3509468ba505cd4978e5d02d3",
    "load_in_4bit": True,
    "bnb_4bit_quant_type": "nf4",
    "bnb_4bit_use_double_quant": True,
    "bnb_4bit_compute_dtype": "bfloat16",
    "attention_implementation": "sdpa",
    "device_map": "auto",
    "local_files_only": True,
    "max_input_tokens": 2048,
    "max_new_tokens": 768,
    "do_sample": False,
    "seed": 42,
    "use_cache": True,
    "skip_special_tokens": True,
    "clean_up_tokenization_spaces": False,
    "repair_generation": False,
    "condition_order": ["base", "adapter"],
    "warm_up_generations": 0,
}


def normalize_problem(problem: str) -> str:
    """Apply the only prompt-side problem normalization frozen for confirmation."""

    normalized = problem.strip()
    if not normalized:
        raise ValueError("problem must not be empty")
    return normalized


def build_confirmatory_messages(problem: str) -> list[dict[str, str]]:
    """Return the exact neutral system and user messages frozen before generation."""

    normalized = normalize_problem(problem)
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": USER_PROMPT_TEMPLATE.format(problem=normalized)},
    ]


def render_confirmatory_prompt(tokenizer: Any, problem: str) -> str:
    """Render with the frozen base tokenizer chat template and generation marker."""

    return tokenizer.apply_chat_template(
        build_confirmatory_messages(problem),
        add_generation_prompt=True,
        tokenize=False,
    )


def serialize_generated_token_ids(token_ids: Iterable[int]) -> bytes:
    """Serialize new-token IDs as compact ASCII JSON for stable hashing and storage."""

    values = [int(token_id) for token_id in token_ids]
    if any(token_id < 0 for token_id in values):
        raise ValueError("token IDs must be nonnegative integers")
    return json.dumps(values, ensure_ascii=True, separators=(",", ":")).encode("ascii")


def hash_generated_token_ids(token_ids: Iterable[int]) -> str:
    """SHA-256 the documented stable token-ID serialization."""

    return hashlib.sha256(serialize_generated_token_ids(token_ids)).hexdigest()
