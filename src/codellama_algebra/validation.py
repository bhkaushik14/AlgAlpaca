"""Strict extraction, syntax checking, and AST policy validation."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass

_PYTHON_FENCE = re.compile(r"```[ \t]*python[ \t]*\r?\n(?P<code>.*?)```", re.IGNORECASE | re.DOTALL)

_ALLOWED_FROM_SYMPY = {
    "Abs",
    "Complement",
    "E",
    "Eq",
    "FiniteSet",
    "I",
    "Interval",
    "Rational",
    "S",
    "Union",
    "ceiling",
    "collect",
    "expand",
    "factor",
    "floor",
    "log",
    "oo",
    "pi",
    "simplify",
    "solve",
    "solveset",
    "sqrt",
    "symbols",
}
_ALLOWED_SYMPY_ATTRIBUTES = _ALLOWED_FROM_SYMPY | {
    "Integer",
    "Symbol",
    "cancel",
    "diff",
    "expand",
    "factor",
    "linsolve",
    "nonlinsolve",
    "solve_univariate_inequality",
    "together",
}
_ALLOWED_VALUE_ATTRIBUTES = {
    "Complexes",
    "EmptySet",
    "Integers",
    "Naturals",
    "Naturals0",
    "Reals",
    "as_set",
    "doit",
    "equals",
    "evalf",
    "expand",
    "factor",
    "subs",
}
_BLOCKED_CALLS = {
    "__import__",
    "breakpoint",
    "compile",
    "delattr",
    "dir",
    "eval",
    "exec",
    "getattr",
    "globals",
    "hasattr",
    "help",
    "input",
    "locals",
    "memoryview",
    "open",
    "setattr",
    "type",
    "vars",
}
_BLOCKED_NODES = (
    ast.AsyncFor,
    ast.AsyncFunctionDef,
    ast.AsyncWith,
    ast.Await,
    ast.ClassDef,
    ast.Delete,
    ast.For,
    ast.FunctionDef,
    ast.Global,
    ast.Lambda,
    ast.ListComp,
    ast.DictComp,
    ast.GeneratorExp,
    ast.Nonlocal,
    ast.Raise,
    ast.SetComp,
    ast.Try,
    ast.While,
    ast.With,
    ast.Yield,
    ast.YieldFrom,
)


@dataclass(frozen=True)
class ValidationResult:
    """A complete validation outcome suitable for logging and stage handoff."""

    valid: bool
    code: str | None
    error_code: str | None = None
    message: str | None = None
    violations: tuple[str, ...] = ()


def extract_python_block(response: str) -> ValidationResult:
    """Extract exactly one Python fence and reject prose or malformed/multiple fences."""

    matches = list(_PYTHON_FENCE.finditer(response))
    if len(matches) > 1:
        return ValidationResult(
            False, None, "multiple_code_blocks", "Expected exactly one code block."
        )
    if not matches:
        code = "malformed_fence" if "```" in response else "no_code_block"
        message = (
            "Malformed Python fence."
            if code == "malformed_fence"
            else "No Python code block found."
        )
        return ValidationResult(False, None, code, message)
    if response.count("```") != 2:
        return ValidationResult(False, None, "malformed_fence", "Unmatched or nested fence marker.")
    match = matches[0]
    if response[: match.start()].strip() or response[match.end() :].strip():
        return ValidationResult(
            False,
            None,
            "surrounding_text",
            "No prose or tags are allowed outside the code block.",
        )
    return ValidationResult(True, match.group("code").strip())


class _PolicyVisitor(ast.NodeVisitor):
    def __init__(self, *, require_answer_print: bool = True) -> None:
        self.violations: list[str] = []
        self.sympy_aliases = {"sp"}
        self.imported_sympy_names: set[str] = set()
        self.print_calls = 0
        self.require_answer_print = require_answer_print

    def reject(self, node: ast.AST, reason: str) -> None:
        self.violations.append(f"line {getattr(node, 'lineno', '?')}: {reason}")

    def generic_visit(self, node: ast.AST) -> None:
        if isinstance(node, _BLOCKED_NODES):
            self.reject(node, f"{type(node).__name__} is not allowed")
            return
        super().generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if alias.name != "sympy":
                self.reject(node, f"import of {alias.name!r} is not allowed")
            else:
                self.sympy_aliases.add(alias.asname or "sympy")

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.level or node.module != "sympy":
            self.reject(node, f"import from {node.module!r} is not allowed")
            return
        for alias in node.names:
            if alias.name == "*" or alias.name not in _ALLOWED_FROM_SYMPY:
                self.reject(node, f"SymPy import {alias.name!r} is not allowlisted")
            else:
                self.imported_sympy_names.add(alias.asname or alias.name)

    def visit_Name(self, node: ast.Name) -> None:
        if "__" in node.id or node.id in _BLOCKED_CALLS:
            self.reject(node, f"name {node.id!r} is blocked")

    def visit_Constant(self, node: ast.Constant) -> None:
        if isinstance(node.value, str):
            self.reject(
                node,
                "string literals are allowed only as direct symbol names or print arguments",
            )

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if node.attr.startswith("_") or "__" in node.attr:
            self.reject(node, "private or dunder attribute access is blocked")
        elif isinstance(node.value, ast.Name) and node.value.id in self.sympy_aliases:
            if node.attr not in _ALLOWED_SYMPY_ATTRIBUTES:
                self.reject(node, f"SymPy attribute {node.attr!r} is not allowlisted")
        elif node.attr not in _ALLOWED_VALUE_ATTRIBUTES:
            self.reject(node, f"attribute {node.attr!r} is not allowlisted")
        self.visit(node.value)

    def visit_Call(self, node: ast.Call) -> None:
        call_name = (
            node.func.id
            if isinstance(node.func, ast.Name)
            else node.func.attr
            if isinstance(node.func, ast.Attribute)
            else None
        )
        if isinstance(node.func, ast.Name):
            if node.func.id in _BLOCKED_CALLS:
                self.reject(node, f"call to {node.func.id!r} is blocked")
            if node.func.id == "print":
                self.print_calls += 1
                if (
                    self.require_answer_print
                    and (
                        len(node.args) < 2
                        or not isinstance(node.args[0], ast.Constant)
                        or node.args[0].value != "ANSWER:"
                        or node.keywords
                    )
                ):
                    self.reject(node, 'print must have the form print("ANSWER:", result)')
                elif not self.require_answer_print and node.keywords:
                    self.reject(node, "print keyword arguments are not allowed")
            elif node.func.id not in self.imported_sympy_names:
                self.reject(node, f"call to non-allowlisted function {node.func.id!r}")
        elif not isinstance(node.func, ast.Attribute):
            self.reject(node, "indirect calls are not allowed")
        self.visit(node.func)
        for argument in node.args:
            if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
                symbol_name = call_name in {"Symbol", "symbols"} and bool(
                    re.fullmatch(
                        r"[A-Za-z][A-Za-z0-9]*(?:\s+[A-Za-z][A-Za-z0-9]*)*",
                        argument.value,
                    )
                )
                if call_name != "print" and not symbol_name:
                    self.reject(argument, "string argument is not allowed for this call")
            else:
                self.visit(argument)
        for keyword in node.keywords:
            self.visit(keyword.value)


def validate_code(code: str) -> ValidationResult:
    """Parse code and enforce the strict allowlist and output policy without executing it."""

    try:
        tree = ast.parse(code, mode="exec")
    except SyntaxError as exc:
        return ValidationResult(False, code, "syntax_error", f"line {exc.lineno}: {exc.msg}")

    visitor = _PolicyVisitor(require_answer_print=True)
    visitor.visit(tree)
    if visitor.print_calls != 1:
        visitor.violations.append('code must contain exactly one print("ANSWER:", result) call')
    if visitor.violations:
        return ValidationResult(
            False,
            code,
            "policy_violation",
            "Code violates the AST allowlist policy.",
            tuple(visitor.violations),
        )
    return ValidationResult(True, code)


def validate_code_compatible(code: str) -> ValidationResult:
    """Apply the same safety allowlist without enforcing the strict stdout contract.

    This secondary policy intentionally permits zero or more ordinary ``print`` calls so
    post-hoc functional analysis can observe the source exactly as generated. It does not add
    imports, calls, attributes, control flow, or any other executable capability.
    """

    try:
        tree = ast.parse(code, mode="exec")
    except SyntaxError as exc:
        return ValidationResult(False, code, "syntax_error", f"line {exc.lineno}: {exc.msg}")

    visitor = _PolicyVisitor(require_answer_print=False)
    visitor.visit(tree)
    if visitor.violations:
        return ValidationResult(
            False,
            code,
            "policy_violation",
            "Code violates the AST allowlist policy.",
            tuple(visitor.violations),
        )
    return ValidationResult(True, code)


def validate_response(response: str) -> ValidationResult:
    """Extract, parse, and apply the strict AST policy to a raw model response."""

    extracted = extract_python_block(response)
    if not extracted.valid or extracted.code is None:
        return extracted
    return validate_code(extracted.code)
