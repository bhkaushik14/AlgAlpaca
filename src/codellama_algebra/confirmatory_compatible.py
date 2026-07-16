"""Future-only compatible extractor with preregistered ambiguity corrections."""

from __future__ import annotations

import ast
import hashlib
import re

from .compatible import CompatibleExtraction, extract_compatible_code

_MARKDOWN_FENCE = re.compile(
    r"```(?P<label>[^\r\n`]*)\r?\n(?P<code>.*?)```",
    re.DOTALL,
)
_LLM_CODE = re.compile(r"<llm-code>(?P<code>.*?)</llm-code>", re.IGNORECASE | re.DOTALL)
_LLM_CODE_OUTPUT = re.compile(
    r"<llm-code-output>.*?</llm-code-output>", re.IGNORECASE | re.DOTALL
)
_SUPPORTED_LABELS = {"", "python", "py", "python3"}
_PROGRAM_EXPRESSION_CALLS = {
    "expand",
    "factor",
    "linsolve",
    "nonlinsolve",
    "print",
    "simplify",
    "solve",
    "solveset",
}


def _rejected(response: str, code: str, message: str, candidates: int = 0) -> CompatibleExtraction:
    return CompatibleExtraction(
        False,
        None,
        None,
        code,
        message,
        hashlib.sha256(response.encode("utf-8")).hexdigest(),
        candidate_count=candidates,
    )


def _parsed_module(text: str) -> ast.Module | None:
    if not text.strip():
        return None
    try:
        return ast.parse(text.strip(), mode="exec")
    except SyntaxError:
        return None


def _is_direct_math_expression(tree: ast.Module) -> bool:
    if len(tree.body) != 1 or not isinstance(tree.body[0], ast.Expr):
        return False
    for node in ast.walk(tree.body[0].value):
        if isinstance(node, ast.Call):
            name = (
                node.func.id
                if isinstance(node.func, ast.Name)
                else node.func.attr
                if isinstance(node.func, ast.Attribute)
                else None
            )
            if name in _PROGRAM_EXPRESSION_CALLS:
                return False
    return True


def _has_competing_raw_source(response: str, spans: list[tuple[int, int]]) -> bool:
    cursor = 0
    for start, end in sorted(spans):
        tree = _parsed_module(response[cursor:start])
        if tree is not None and not _is_direct_math_expression(tree):
            return True
        cursor = max(cursor, end)
    tree = _parsed_module(response[cursor:])
    return tree is not None and not _is_direct_math_expression(tree)


def extract_confirmatory_code(response: str) -> CompatibleExtraction:
    """Use the Stage 2B baseline after rejecting newly demonstrated ambiguous/nonprogram forms."""

    markdown = list(_MARKDOWN_FENCE.finditer(response))
    legacy = list(_LLM_CODE.finditer(response))
    outputs = list(_LLM_CODE_OUTPUT.finditer(response))
    labels = [match.group("label").strip().casefold() for match in markdown]
    plausible = sum(label in _SUPPORTED_LABELS for label in labels) + len(legacy)

    tag_starts = len(re.findall(r"</?llm-code", response, re.IGNORECASE))
    complete_tags = len(re.findall(r"</?llm-code(?:-output)?>", response, re.IGNORECASE))
    malformed = bool(
        response.count("```") != 2 * len(markdown)
        or len(re.findall(r"<llm-code>", response, re.IGNORECASE)) != len(legacy)
        or len(re.findall(r"</llm-code>", response, re.IGNORECASE)) != len(legacy)
        or len(re.findall(r"<llm-code-output>", response, re.IGNORECASE)) != len(outputs)
        or len(re.findall(r"</llm-code-output>", response, re.IGNORECASE)) != len(outputs)
        or tag_starts != complete_tags
    )
    if malformed:
        return _rejected(
            response,
            "malformed_or_unsupported_wrapper",
            "Wrapper markup is malformed or incomplete.",
            plausible,
        )
    if any(label not in _SUPPORTED_LABELS for label in labels):
        return _rejected(
            response,
            "unsupported_wrapper",
            "A non-Python Markdown fence is present.",
            plausible,
        )

    spans = [(match.start(), match.end()) for match in markdown + legacy + outputs]
    if plausible == 1 and _has_competing_raw_source(response, spans):
        return _rejected(
            response,
            "ambiguous_code_blocks",
            "A wrapped program and a competing raw program are both present.",
            2,
        )

    if not spans:
        tree = _parsed_module(response)
        if tree is not None and _is_direct_math_expression(tree):
            return _rejected(
                response,
                "direct_answer_not_program",
                "A bare mathematical expression is not converted into a program.",
            )
    return extract_compatible_code(response)
