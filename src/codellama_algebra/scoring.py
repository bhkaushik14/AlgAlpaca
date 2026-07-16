"""Schema-controlled symbolic scoring in a separate isolated worker process."""

from __future__ import annotations

import argparse
import ast
import json
import os
import resource
import signal
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

ANSWER_KINDS = {
    "exact_number",
    "symbolic_expression",
    "finite_set",
    "variable_mapping",
    "interval_set",
    "approximate_numeric",
}


@dataclass(frozen=True)
class ExpectedAnswer:
    """Controlled expected-answer schema used by fixtures and scoring."""

    kind: str
    value: str | list[str] | dict[str, str]
    variables: tuple[str, ...] = ()
    domain_exclusions: tuple[str, ...] = ()
    tolerance: float | None = None

    def __post_init__(self) -> None:
        if self.kind not in ANSWER_KINDS:
            raise ValueError(f"unsupported expected-answer kind: {self.kind}")
        if self.kind == "approximate_numeric":
            if self.tolerance is None or self.tolerance <= 0:
                raise ValueError("approximate_numeric requires a positive tolerance")
        elif self.tolerance is not None:
            raise ValueError("tolerance is allowed only for approximate_numeric")
        if self.kind == "finite_set" and not isinstance(self.value, list):
            raise ValueError("finite_set value must be a list")
        if self.kind == "variable_mapping" and not isinstance(self.value, dict):
            raise ValueError("variable_mapping value must be an object")
        if self.kind not in {"finite_set", "variable_mapping"} and not isinstance(self.value, str):
            raise ValueError(f"{self.kind} value must be a string")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExpectedAnswer":
        return cls(
            kind=data["kind"],
            value=data["value"],
            variables=tuple(data.get("variables", ())),
            domain_exclusions=tuple(data.get("domain_exclusions", ())),
            tolerance=data.get("tolerance"),
        )


@dataclass(frozen=True)
class ScoreResult:
    """Correctness plus a stable failure category and worker detail."""

    correct: bool
    error_code: str | None = None
    message: str | None = None
    normalized_actual: str | None = None


def _worker_limits() -> None:
    resource.setrlimit(resource.RLIMIT_CPU, (2, 2))
    resource.setrlimit(resource.RLIMIT_AS, (768 * 1024 * 1024, 768 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_FSIZE, (1024 * 1024, 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_NOFILE, (32, 32))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    if hasattr(resource, "RLIMIT_NPROC"):
        resource.setrlimit(resource.RLIMIT_NPROC, (1, 1))


def score_answer(
    actual: str,
    expected: ExpectedAnswer | dict[str, Any],
    timeout_seconds: float = 3.0,
) -> ScoreResult:
    """Score in an isolated worker so the parent never symbolically parses actual output."""

    schema = (
        expected if isinstance(expected, ExpectedAnswer) else ExpectedAnswer.from_dict(expected)
    )
    payload = json.dumps({"actual": actual, "expected": asdict(schema)}).encode("utf-8")
    if len(payload) > 32 * 1024:
        return ScoreResult(False, "input_too_large", "Scoring input exceeds 32 KiB.")
    if os.name != "posix":
        return ScoreResult(False, "platform_error", "Isolated POSIX scoring worker unavailable.")

    with tempfile.TemporaryDirectory(prefix="algebra-score-") as temp_dir:
        process = subprocess.Popen(
            [sys.executable, "-I", str(Path(__file__).resolve()), "--worker"],
            cwd=temp_dir,
            env={"HOME": temp_dir, "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "PATH": os.defpath},
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
            preexec_fn=_worker_limits,
        )
        try:
            stdout, stderr = process.communicate(payload, timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
            return ScoreResult(False, "scoring_timeout", "Symbolic scoring timed out.")
    if len(stdout) > 64 * 1024 or len(stderr) > 64 * 1024:
        return ScoreResult(False, "worker_output_limit", "Scoring worker output exceeded 64 KiB.")
    if process.returncode != 0:
        detail = stderr.decode("utf-8", errors="replace")[-1000:]
        return ScoreResult(False, "worker_failure", detail or "Scoring worker failed.")
    try:
        return ScoreResult(**json.loads(stdout.decode("utf-8")))
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError) as exc:
        return ScoreResult(False, "worker_protocol_error", str(exc))


def _safe_expression(
    text: str, variables: tuple[str, ...], sp: Any, *, allow_relational: bool = False
) -> Any:
    text = text.strip().replace("^", "**").replace("∞", "oo")
    if not text or len(text) > 2048:
        raise ValueError("expression is empty or too long")
    tree = ast.parse(text, mode="eval")
    allowed_names = set(variables) | {
        "Abs",
        "Complement",
        "E",
        "FiniteSet",
        "I",
        "Interval",
        "Rational",
        "Union",
        "log",
        "oo",
        "pi",
        "sqrt",
    }
    allowed_nodes = (
        ast.Expression,
        ast.BinOp,
        ast.UnaryOp,
        ast.Constant,
        ast.Name,
        ast.Call,
        ast.Attribute,
        ast.List,
        ast.Tuple,
        ast.Set,
        ast.Dict,
        ast.Load,
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.Div,
        ast.Pow,
        ast.Mod,
        ast.USub,
        ast.UAdd,
    )
    if allow_relational:
        allowed_nodes += (ast.BitAnd, ast.BitOr, ast.Compare, ast.Lt, ast.LtE, ast.Gt, ast.GtE)
    for node in ast.walk(tree):
        if not isinstance(node, allowed_nodes):
            raise ValueError(f"unsupported expression syntax: {type(node).__name__}")
        if isinstance(node, ast.Name) and node.id not in allowed_names:
            raise ValueError(f"unknown expression name: {node.id}")
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                if node.func.id not in allowed_names - set(variables):
                    raise ValueError(f"unsupported expression call: {node.func.id}")
            elif not (
                isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "Interval"
                and node.func.attr in {"open", "closed", "Lopen", "Ropen"}
            ):
                raise ValueError("unsupported attribute call")
        if isinstance(node, ast.Attribute) and not (
            isinstance(node.value, ast.Name)
            and node.value.id == "Interval"
            and node.attr in {"open", "closed", "Lopen", "Ropen"}
        ):
            raise ValueError("unsupported attribute access")

    local = {name: sp.Symbol(name) for name in variables}
    local.update(
        {
            "Abs": sp.Abs,
            "Complement": sp.Complement,
            "E": sp.E,
            "FiniteSet": sp.FiniteSet,
            "I": sp.I,
            "Interval": sp.Interval,
            "Rational": sp.Rational,
            "Union": sp.Union,
            "log": sp.log,
            "oo": sp.oo,
            "pi": sp.pi,
            "sqrt": sp.sqrt,
        }
    )
    return sp.sympify(text, locals=local, evaluate=True)


def _strip_answer_prefix(actual: str) -> str:
    actual = actual.strip()
    if actual.startswith("ANSWER:"):
        actual = actual[len("ANSWER:") :].strip()
    if "\n" in actual or not actual:
        raise ValueError("actual answer must be one nonempty line")
    return actual


def _finite_set(text: str, variables: tuple[str, ...], sp: Any) -> Any:
    text = text.strip()
    if text in {"EmptySet", "set()", "[]", "{}"}:
        return sp.EmptySet
    parsed = _safe_expression(text, variables, sp)
    if isinstance(parsed, sp.FiniteSet):
        return parsed
    if isinstance(parsed, (list, tuple, set)):
        return sp.FiniteSet(*parsed)
    return sp.FiniteSet(parsed)


def _mapping(text: str, variables: tuple[str, ...], sp: Any) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("[{") and text.endswith("}]"):
        text = text[1:-1]
    if text.startswith("{") and text.endswith("}"):
        text = text[1:-1]
    pieces = [piece.strip() for piece in text.split(",") if piece.strip()]
    result: dict[str, Any] = {}
    for piece in pieces:
        separator = ":" if ":" in piece else "=" if "=" in piece else None
        if separator is None:
            raise ValueError("mapping entries must use ':' or '='")
        key, value = [part.strip().strip("'\"") for part in piece.split(separator, 1)]
        if key not in variables or key in result:
            raise ValueError(f"unexpected or duplicate mapping variable: {key}")
        result[key] = _safe_expression(value, variables, sp)
    return result


def _equivalent(left: Any, right: Any, sp: Any) -> bool:
    return bool(sp.simplify(left - right) == 0)


def _score_in_worker(actual: str, expected: ExpectedAnswer) -> ScoreResult:
    import sympy as sp

    try:
        actual = _strip_answer_prefix(actual)
        variables = expected.variables
        if expected.kind == "exact_number":
            actual_value = _safe_expression(actual, variables, sp)
            expected_value = _safe_expression(str(expected.value), variables, sp)
            if actual_value.free_symbols:
                raise ValueError("exact number contains free symbols")
            correct = _equivalent(actual_value, expected_value, sp)
            normalized = sp.sstr(actual_value)
        elif expected.kind == "symbolic_expression":
            actual_value = _safe_expression(actual, variables, sp)
            expected_value = _safe_expression(str(expected.value), variables, sp)
            allowed_symbols = {sp.Symbol(name) for name in variables}
            if not actual_value.free_symbols <= allowed_symbols:
                raise ValueError("symbolic expression contains unexpected variables")
            correct = _equivalent(actual_value, expected_value, sp)
            normalized = sp.sstr(actual_value)
        elif expected.kind == "finite_set":
            actual_set = _finite_set(actual, variables, sp)
            expected_set = sp.FiniteSet(
                *[_safe_expression(item, variables, sp) for item in expected.value]
            )
            exclusions = sp.FiniteSet(
                *[_safe_expression(item, variables, sp) for item in expected.domain_exclusions]
            )
            correct = actual_set == expected_set and actual_set.intersect(exclusions) == sp.EmptySet
            normalized = sp.sstr(actual_set)
        elif expected.kind == "variable_mapping":
            actual_mapping = _mapping(actual, variables, sp)
            expected_mapping = {
                key: _safe_expression(value, variables, sp) for key, value in expected.value.items()
            }
            correct = actual_mapping.keys() == expected_mapping.keys() and all(
                _equivalent(actual_mapping[key], expected_mapping[key], sp)
                for key in expected_mapping
            )
            normalized = str({key: sp.sstr(value) for key, value in actual_mapping.items()})
        elif expected.kind == "interval_set":
            actual_set = _safe_expression(actual, variables, sp, allow_relational=True)
            expected_set = _safe_expression(str(expected.value), variables, sp)
            if isinstance(actual_set, sp.logic.boolalg.Boolean):
                actual_set = actual_set.as_set()
            if not isinstance(actual_set, sp.Set):
                raise ValueError("interval answer is not a SymPy set")
            correct = actual_set == expected_set
            normalized = sp.sstr(actual_set)
        else:
            actual_value = _safe_expression(actual, variables, sp)
            expected_value = _safe_expression(str(expected.value), variables, sp)
            if actual_value.free_symbols:
                raise ValueError("approximate number contains free symbols")
            difference = abs(float(sp.N(actual_value - expected_value, 17)))
            correct = difference <= float(expected.tolerance)
            normalized = str(float(sp.N(actual_value, 17)))
    except (ValueError, SyntaxError, TypeError, AttributeError) as exc:
        return ScoreResult(False, "malformed_answer", str(exc))
    if correct:
        return ScoreResult(True, normalized_actual=normalized)
    return ScoreResult(False, "incorrect_answer", "Actual answer is not equivalent.", normalized)


def _worker_main() -> int:
    try:
        payload = json.loads(sys.stdin.buffer.read(32 * 1024 + 1))
        expected = ExpectedAnswer.from_dict(payload["expected"])
        result = _score_in_worker(str(payload["actual"]), expected)
        sys.stdout.write(json.dumps(asdict(result)))
        return 0
    except Exception as exc:
        sys.stderr.write(f"worker protocol failure: {exc}")
        return 2


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not args.worker:
        parser.error("This module's command line is reserved for its isolated worker.")
    return _worker_main()


if __name__ == "__main__":
    raise SystemExit(main())
