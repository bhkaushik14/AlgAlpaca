"""Canonical public algebra-to-SymPy inference prompt."""

from __future__ import annotations

from typing import Any

PROMPT_VERSION = "algebra-to-sympy-v1"
REPAIR_PROMPT_VERSION = "format-repair-v1"

SYSTEM_PROMPT = (
    "You generate minimal Python code for algebra problems. "
    "Return exactly one fenced Python code block and no other text."
)


def normalize_problem(problem: str) -> str:
    """Trim a problem and remove one matching pair of surrounding quotes."""

    normalized = problem.strip()
    if len(normalized) >= 2 and normalized[0] == normalized[-1] and normalized[0] in {"'", '"'}:
        normalized = normalized[1:-1].strip()
    if not normalized:
        raise ValueError("problem must not be empty")
    return normalized


def build_messages(problem: str) -> list[dict[str, str]]:
    """Build the new public inference contract; historical targets were less consistent."""

    problem = normalize_problem(problem)
    user = f"""Write Python code that solves this algebra problem.

Contract:
- Return exactly one ```python fenced code block and no prose outside it.
- Use SymPy for symbolic computation when needed.
- Produce exactly one output line, using print(\"ANSWER:\", result).
- Do not read or write files.
- Do not use network access, processes, shells, environment variables, or interactive input.
- Keep all computation in straight-line assignments and expressions.

Problem:
{problem}
"""
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]


def render_prompt(tokenizer: Any, problem: str) -> str:
    """Render the canonical messages with the tokenizer chat template when available."""

    messages = build_messages(problem)
    if hasattr(tokenizer, "apply_chat_template"):
        return tokenizer.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=False,
        )
    return (
        f"<<SYS>>{messages[0]['content']}<</SYS>>\n"
        f"[INST]{messages[1]['content']}[/INST]"
    )


def build_repair_prompt(original_prompt: str, malformed_response: str) -> str:
    """Request one format-only repair while retaining the malformed response for context."""

    return (
        f"{original_prompt}\n\n"
        "The previous response violated the output contract. Rewrite it once. Return exactly one "
        "fenced Python block, no surrounding prose, and exactly one print(\"ANSWER:\", result) "
        f"line. Previous response:\n{malformed_response}"
    )
