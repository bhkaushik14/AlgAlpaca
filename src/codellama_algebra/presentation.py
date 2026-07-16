"""Safe, presentation-only formatting for local web results.

This module never changes generated source, observable stdout parsing, or evaluation.
"""

from __future__ import annotations

import ast
import math
import re
from dataclasses import dataclass
from typing import Any

import sympy as sp

GENERIC_RUNTIME_ERROR = (
    "The program exited with an error, but no additional safe detail was available."
)
SYNTAX_ERROR_SUMMARY = "The generated program contains invalid Python syntax."
MAX_ERROR_SUMMARY = 220
_ANSI = re.compile(r"\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07]*(?:\x07|\x1b\\))")
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_UNIX_PATH = re.compile(r"(?<![\w.-])(?:~|/)(?:[^\s:'\"]+/)*[^\s:'\"]*")
_WINDOWS_PATH = re.compile(r"(?i)\b[A-Z]:\\(?:[^\s:'\"]+\\)*[^\s:'\"]*")
_ENV_REFERENCE = re.compile(r"\$\{?[A-Za-z_][A-Za-z0-9_]*\}?|%[A-Za-z_][A-Za-z0-9_]*%")
_SENSITIVE = re.compile(r"(?i)\b(?:token|password|secret|authorization|api[_-]?key)\b")
_IDENTITY = re.compile(r"(?i)\b(?:user(?:name)?|host(?:name)?|home|cache)\b")
_EXCEPTION = re.compile(
    r"^(?P<kind>[A-Za-z_][A-Za-z0-9_.]*(?:Error|Exception|Interrupt))"
    r"(?:\s*:\s*(?P<message>.*))?$"
)


def _safe_error_line(line: str) -> str:
    line = _WINDOWS_PATH.sub("<local-path>", line)
    line = _UNIX_PATH.sub("<local-path>", line)
    line = _ENV_REFERENCE.sub("<environment-value>", line)
    line = re.sub(r"(?i)\b[^\s]*(?:cache|huggingface|transformers)[^\s]*", "<local-path>", line)
    line = re.sub(r"\s+", " ", line).strip()
    if _SENSITIVE.search(line) or _IDENTITY.search(line):
        return ""
    return line


def summarize_runtime_error(stderr: str) -> str:
    """Extract one bounded exception line from already-bounded, sanitized stderr."""

    cleaned = _CONTROL.sub("", _ANSI.sub("", stderr))
    candidates: list[str] = []
    for raw_line in cleaned.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("Traceback (most recent call last)"):
            continue
        if line.startswith('File "') or line.startswith("File '<local-path>'"):
            continue
        if line == "^" or set(line) <= {"^", "~", " ", "\t"}:
            continue
        match = _EXCEPTION.fullmatch(line)
        if not match:
            continue
        kind = match.group("kind").rsplit(".", 1)[-1]
        raw_message = match.group("message") or ""
        message = _safe_error_line(raw_message)
        if raw_message and not message:
            continue
        summary = f"{kind}: {message}" if message else kind
        candidates.append(summary)
    if not candidates:
        return GENERIC_RUNTIME_ERROR
    summary = candidates[-1]
    if len(summary) > MAX_ERROR_SUMMARY:
        summary = summary[: MAX_ERROR_SUMMARY - 1].rstrip() + "…"
    return summary


_REAL_DOMAIN = re.compile(
    r"\b(?:over\s+the\s+real\s+numbers|over\s+the\s+reals|real\s+solutions?|real\s+roots?)\b",
    re.IGNORECASE,
)
_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class DisplayParseError(ValueError):
    """An input is outside the small display-expression language."""


@dataclass(frozen=True)
class DisplayResult:
    value: str
    kind: str


class _NumericInterpreter:
    MAX_NODES = 256
    MAX_DEPTH = 32
    MAX_COLLECTION = 100
    MAX_INTEGER_DIGITS = 100

    def __init__(self, text: str) -> None:
        try:
            self.tree = ast.parse(text, mode="eval")
        except (SyntaxError, ValueError) as exc:
            raise DisplayParseError("invalid expression") from exc
        if sum(1 for _ in ast.walk(self.tree)) > self.MAX_NODES:
            raise DisplayParseError("expression is too large")

    def parse(self) -> Any:
        return self._visit(self.tree.body, 0)

    def _visit(self, node: ast.AST, depth: int) -> Any:
        if depth > self.MAX_DEPTH:
            raise DisplayParseError("expression is too deep")
        def visit(child: ast.AST) -> Any:
            return self._visit(child, depth + 1)
        if isinstance(node, ast.Constant):
            if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
                raise DisplayParseError("constant is not numeric")
            if isinstance(node.value, int):
                if len(str(abs(node.value))) > self.MAX_INTEGER_DIGITS:
                    raise DisplayParseError("integer is too large")
                return sp.Integer(node.value)
            if not math.isfinite(node.value):
                raise DisplayParseError("float is not finite")
            return sp.Float(node.value)
        if isinstance(node, ast.Name):
            values = {"I": sp.I, "pi": sp.pi, "E": sp.E}
            if node.id not in values:
                raise DisplayParseError("name is not allowed")
            return values[node.id]
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = visit(node.operand)
            return value if isinstance(node.op, ast.UAdd) else -value
        if isinstance(node, ast.BinOp) and isinstance(
            node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow)
        ):
            left, right = visit(node.left), visit(node.right)
            if not isinstance(left, sp.Expr) or not isinstance(right, sp.Expr):
                raise DisplayParseError("collection arithmetic is not allowed")
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if isinstance(node.op, ast.Div):
                if right == 0:
                    raise DisplayParseError("division by zero")
                return left / right
            if right.is_real is not True or right.is_finite is not True:
                raise DisplayParseError("exponent is not a finite real number")
            exponent = float(sp.N(right, 16))
            if not math.isfinite(exponent) or abs(exponent) > 100:
                raise DisplayParseError("exponent is outside the display bound")
            return left**right
        if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
            if len(node.elts) > self.MAX_COLLECTION:
                raise DisplayParseError("collection is too large")
            values = [visit(item) for item in node.elts]
            if isinstance(node, ast.List):
                return values
            if isinstance(node, ast.Tuple):
                return tuple(values)
            return frozenset(values)
        if isinstance(node, ast.Dict):
            if len(node.keys) > self.MAX_COLLECTION or any(key is None for key in node.keys):
                raise DisplayParseError("dictionary is too large")
            result: list[tuple[str, Any]] = []
            for key_node, value_node in zip(node.keys, node.values, strict=True):
                assert key_node is not None
                if isinstance(key_node, ast.Name) and _IDENTIFIER.fullmatch(key_node.id):
                    key = key_node.id
                elif (
                    isinstance(key_node, ast.Constant)
                    and isinstance(key_node.value, str)
                    and _IDENTIFIER.fullmatch(key_node.value)
                ):
                    key = key_node.value
                else:
                    raise DisplayParseError("dictionary key is not an inert label")
                result.append((key, visit(value_node)))
            return result
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.keywords:
                raise DisplayParseError("keyword arguments are not allowed")
            functions = {
                "sqrt": (sp.sqrt, 1, 1),
                "Rational": (sp.Rational, 2, 2),
                "Integer": (sp.Integer, 1, 1),
                "Float": (sp.Float, 1, 1),
            }
            if node.func.id not in functions:
                raise DisplayParseError("function is not allowed")
            function, minimum, maximum = functions[node.func.id]
            if not minimum <= len(node.args) <= maximum:
                raise DisplayParseError("wrong argument count")
            args = [visit(arg) for arg in node.args]
            try:
                return function(*args)
            except (ArithmeticError, TypeError, ValueError) as exc:
                raise DisplayParseError("numeric construction failed") from exc
        raise DisplayParseError(f"{type(node).__name__} is not allowed")


def _numeric_parts(value: sp.Expr) -> tuple[float, float]:
    if value.is_number is not True or value.is_finite is not True:
        raise DisplayParseError("value is not a finite number")
    numeric = sp.N(value, 16)
    real = float(sp.re(numeric))
    imaginary = float(sp.im(numeric))
    if not math.isfinite(real) or not math.isfinite(imaginary):
        raise DisplayParseError("value is not finite")
    return real, imaginary


def _format_real(value: float) -> str:
    if abs(value) <= 0.0005:
        value = 0.0
    nearest = round(value)
    if abs(value - nearest) <= 1e-12:
        return str(nearest)
    return f"{value:.3f}"


def _format_number(value: sp.Expr, real_only: bool) -> str | None:
    real, imaginary = _numeric_parts(value)
    if abs(imaginary) <= 1e-10:
        return _format_real(real)
    if real_only:
        return None
    sign = "+" if imaginary >= 0 else "-"
    imaginary_text = _format_real(abs(imaginary))
    if abs(real) <= 1e-12:
        return f"{'-' if imaginary < 0 else ''}{imaginary_text}i"
    return f"{_format_real(real)} {sign} {imaginary_text}i"


def _format_value(value: Any, real_only: bool) -> tuple[str, int]:
    if isinstance(value, sp.Expr):
        rendered = _format_number(value, real_only)
        return (rendered or "", int(rendered is not None))
    if isinstance(value, list):
        items = [_format_value(item, real_only) for item in value]
        kept = [text for text, count in items if count]
        return f"[{', '.join(kept)}]", sum(count for _, count in items)
    if isinstance(value, tuple):
        items = [_format_value(item, real_only) for item in value]
        kept = [text for text, count in items if count]
        suffix = "," if len(kept) == 1 else ""
        return f"({', '.join(kept)}{suffix})", sum(count for _, count in items)
    if isinstance(value, frozenset):
        items = sorted((_format_value(item, real_only) for item in value), key=lambda item: item[0])
        kept = [text for text, count in items if count]
        return "{" + ", ".join(kept) + "}", sum(count for _, count in items)
    if isinstance(value, list) and value and isinstance(value[0], tuple):
        raise AssertionError("unreachable")
    # Dictionaries are represented as an ordered list of inert-label pairs.
    if isinstance(value, list):
        raise DisplayParseError("unsupported collection")
    if isinstance(value, tuple):
        raise DisplayParseError("unsupported collection")
    raise DisplayParseError("unsupported value")


def _format_interpreted(value: Any, real_only: bool) -> tuple[str, int]:
    if isinstance(value, list) and value and all(
        isinstance(item, tuple) and len(item) == 2 and isinstance(item[0], str) for item in value
    ):
        items: list[str] = []
        count = 0
        for key, item in value:
            rendered, item_count = _format_interpreted(item, real_only)
            if item_count:
                items.append(f"{key}: {rendered}")
                count += item_count
        return "{" + ", ".join(items) + "}", count
    if isinstance(value, sp.Expr):
        rendered = _format_number(value, real_only)
        return (rendered or "", int(rendered is not None))
    if isinstance(value, list):
        items = [_format_interpreted(item, real_only) for item in value]
        kept = [text for text, count in items if count]
        return f"[{', '.join(kept)}]", sum(count for _, count in items)
    if isinstance(value, tuple):
        items = [_format_interpreted(item, real_only) for item in value]
        kept = [text for text, count in items if count]
        suffix = "," if len(kept) == 1 else ""
        return f"({', '.join(kept)}{suffix})", sum(count for _, count in items)
    if isinstance(value, frozenset):
        items = sorted(
            (_format_interpreted(item, real_only) for item in value), key=lambda item: item[0]
        )
        kept = [text for text, count in items if count]
        return "{" + ", ".join(kept) + "}", sum(count for _, count in items)
    raise DisplayParseError("unsupported value")


def _is_exact_integer_structure(value: Any) -> bool:
    if isinstance(value, sp.Integer):
        return True
    if isinstance(value, (list, tuple, frozenset)):
        return all(_is_exact_integer_structure(item) for item in value)
    return False


def numeric_display(parsed_value: str, problem: str) -> DisplayResult:
    """Return a safe concise display without executing or rewriting the source text."""

    if not parsed_value:
        return DisplayResult("", "none")
    try:
        interpreted = _NumericInterpreter(parsed_value).parse()
        if _is_exact_integer_structure(interpreted):
            return DisplayResult(parsed_value, "exact")
        rendered, count = _format_interpreted(interpreted, bool(_REAL_DOMAIN.search(problem)))
        if count == 0:
            raise DisplayParseError("real-domain filtering removed every value")
        return DisplayResult(rendered, "approximate")
    except (DisplayParseError, ArithmeticError, OverflowError, TypeError, ValueError):
        return DisplayResult(parsed_value, "exact")
