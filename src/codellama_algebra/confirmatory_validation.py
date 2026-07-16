"""Future-only static policy frozen for the preregistered confirmatory evaluation.

The Stage 2B implementation remains untouched. This module inherits that implementation and
corrects one demonstrated allowlist inconsistency: safe SymPy names that were already allowed as
``sp.<name>`` are also allowed through explicit ``from sympy import <name>`` statements.
"""

from __future__ import annotations

import ast

from .validation import ValidationResult, _ALLOWED_FROM_SYMPY, _PolicyVisitor

_ADDITIONAL_SAFE_FROM_IMPORTS = {
    "Integer",
    "Symbol",
    "cancel",
    "diff",
    "linsolve",
    "nonlinsolve",
    "solve_univariate_inequality",
    "together",
}
_CONFIRMATORY_ALLOWED_FROM_SYMPY = _ALLOWED_FROM_SYMPY | _ADDITIONAL_SAFE_FROM_IMPORTS


class _ConfirmatoryPolicyVisitor(_PolicyVisitor):
    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.level or node.module != "sympy":
            self.reject(node, f"import from {node.module!r} is not allowed")
            return
        for alias in node.names:
            if alias.name == "*" or alias.name not in _CONFIRMATORY_ALLOWED_FROM_SYMPY:
                self.reject(node, f"SymPy import {alias.name!r} is not allowlisted")
            else:
                self.imported_sympy_names.add(alias.asname or alias.name)


def validate_confirmatory_code(code: str) -> ValidationResult:
    """Parse code and enforce the corrected future safety allowlist without a print contract."""

    try:
        tree = ast.parse(code, mode="exec")
    except SyntaxError as exc:
        return ValidationResult(False, code, "syntax_error", f"line {exc.lineno}: {exc.msg}")

    visitor = _ConfirmatoryPolicyVisitor(require_answer_print=False)
    visitor.visit(tree)
    if visitor.violations:
        return ValidationResult(
            False,
            code,
            "policy_violation",
            "Code violates the confirmatory AST allowlist policy.",
            tuple(visitor.violations),
        )
    return ValidationResult(True, code)
