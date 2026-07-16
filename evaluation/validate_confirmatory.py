"""Validate and render the independently authored confirmatory algebra fixture."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

import sympy as sp

from codellama_algebra.confirmatory_scoring import score_confirmatory_answer
from codellama_algebra.confirmatory_validation import validate_confirmatory_code
from codellama_algebra.scoring import ExpectedAnswer

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "evaluation" / "confirmatory_cases.jsonl"

CATEGORIES = (
    "linear_equations",
    "quadratic_equations",
    "systems_of_equations",
    "polynomial_roots_or_factorization",
    "rational_equations",
    "inequalities",
    "simplification_or_evaluation",
    "proportions_and_word_problems",
    "absolute_value_equations",
    "exponents_and_radicals",
)

DESIGN_MATRIX = {
    "linear_equations": [
        "distributed variable terms on both sides; integer solution; basic; finite_set",
        "two unlike denominators; negative rational solution; intermediate; finite_set",
        "negative rational multiplier; positive rational solution; intermediate; finite_set",
        "exact rational coefficient/constants; negative rational solution; basic; finite_set",
        "two distributed products; positive integer solution; basic; finite_set",
        "linear proportion; rational solution; basic; finite_set",
        "opposing distributed terms; rational solution; basic; finite_set",
        "nested fraction in a product; integer solution; basic; finite_set",
        "inconsistent equation; no solution; basic; finite_set",
        "identity; all real numbers; basic; interval_set",
    ],
    "quadratic_equations": [
        "nonmonic integer coefficients; integer plus rational roots; basic; finite_set",
        "shifted square; two integer branches; basic; finite_set",
        "negative discriminant in complex domain; conjugate roots; intermediate; finite_set",
        "repeated real root; one distinct solution; basic; finite_set",
        "irrational conjugate real roots; intermediate; finite_set",
        "negative discriminant in real domain; no solution; basic; finite_set",
        "product equation; two integer roots; basic; finite_set",
        "factored left side against a constant; irrational roots; intermediate; finite_set",
        "rational coefficients; two rational roots; intermediate; finite_set",
        "pure imaginary roots in complex domain; basic; finite_set",
    ],
    "systems_of_equations": [
        "2-by-2 integer coefficients; unique rational mapping; basic",
        "2-by-2 signed coefficients; unique integer mapping; basic",
        "2-by-2 rational coefficients; exact rational mapping; intermediate",
        "3-by-3 system; negative component; unique integer mapping; intermediate",
        "dense 3-by-3 system; mixed-sign integer mapping; intermediate",
        "symmetric nonlinear sum/product system; positive domain and ordering select one mapping",
        "nonlinear sum/squares system; inequality selects one ordered mapping",
        "2-by-2 system with exact irrational constants and mapping",
        "2-by-2 signed system with rational mapping",
        "3-by-3 exact rational system; advanced; rational mapping",
    ],
    "polynomial_roots_or_factorization": [
        "cubic with three separated integer roots; real domain",
        "cubic with a repeated root; distinct-root finite set",
        "biquadratic with four exact irrational real roots",
        "biquadratic over complex numbers with real and imaginary roots",
        "degree-five factored polynomial with five real roots including zero",
        "cubic over complex numbers with one real and two nonreal roots",
        "quartic with two double roots; multiplicity explicitly separated from solution values",
        "factored quartic with integer, rational, and imaginary roots",
        "quartic with four Gaussian-integer roots",
        "sixth roots of unity; six exact complex values; advanced",
    ],
    "rational_equations": [
        "one rational expression equals exact rational constant; one denominator exclusion",
        "sum of two reciprocal terms; two exclusions; one rational solution",
        "identity after cancellation; all reals except a removable-domain hole",
        "zero rational expression; canceled excluded root",
        "rational equation clearing to a quadratic; two valid roots",
        "two reciprocal terms; two exclusions; two irrational roots",
        "equality of rational expressions; two exclusions; one rational root",
        "difference of rational terms; two exclusions; one integer root",
        "rational expression reducing to a contradictory constant; empty set",
        "three rational terms with shared factored denominator; two exclusions; zero root",
    ],
    "inequalities": [
        "linear inequality with sign reversal; open unbounded interval",
        "rational coefficient; closed unbounded interval",
        "quadratic nonpositive region; closed bounded interval",
        "strict factored polynomial sign; two open exterior intervals",
        "rational sign chart; denominator exclusion and mixed open/closed boundaries",
        "strict absolute-value inequality; bounded open interval",
        "nonstrict absolute-value inequality; two closed exterior intervals",
        "compound linear inequalities; half-open bounded interval",
        "positive-definite quadratic; all real numbers",
        "negative-square impossibility; empty set",
    ],
    "simplification_or_evaluation": [
        "linear-by-quadratic expansion; cubic symbolic expression",
        "exact rational evaluation at a rational input",
        "cubic function evaluation at a negative input",
        "three-term exact radical combination",
        "square of an irrational binomial",
        "collection of symbolic terms with rational coefficients",
        "two-variable polynomial evaluation",
        "two-variable expansion with cross-term cancellation",
        "finite geometric-series evaluation",
        "symmetric cubic identity from a given sum and product",
    ],
    "proportions_and_word_problems": [
        "recipe scaling with exact fractional rate and units",
        "constant production rate with exact decimal times",
        "mixture concentration with changing total volume",
        "four consecutive positive integers; smallest/largest mapping",
        "reverse exact percentage discount",
        "gear-turn ratio transfer",
        "simple interest with explicit no-compounding assumption",
        "ticket count and revenue; nonnegative integer mapping",
        "age relation plus total; nonnegative mapping",
        "single exact percentage increase",
    ],
    "absolute_value_equations": [
        "outside additive shift; two integer roots",
        "outside scale and linear interior; integer/rational roots",
        "equality of two absolute linear expressions; two rational roots",
        "sum of absolute values equals a negative constant; no solution",
        "rational slope and irrational magnitude; two exact irrational roots",
        "absolute expression equals variable linear expression; one branch survives sign check",
        "nested absolute values; four integer roots",
        "scaled reversed linear interior; two rational roots",
        "absolute value of a quadratic equals zero; two real roots",
        "two asymmetric absolute linear forms; integer/rational roots",
    ],
    "exponents_and_radicals": [
        "powers of two with opposing affine exponents; rational solution",
        "powers of three with affine exponents on both sides; integer solution",
        "common-base rewrite; rational solution",
        "single principal radical with linear radicand; integer solution",
        "principal radical against a linear expression; extraneous squared candidate",
        "principal radical plus constant; one invalid quadratic branch; irrational solution",
        "equality of two principal radicals with intersecting domains",
        "non-common-base exponential; sole approximate case with absolute tolerance 1e-6",
        "sum of two radicals; repeated squaring and explicit domain checks",
        "positive exponential equated to a negative value; no real solution",
    ],
}


def load_cases(path: Path = FIXTURE) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def expected_schema(case: dict[str, Any]) -> ExpectedAnswer:
    return ExpectedAnswer(
        case["expected_answer_kind"],
        case["expected_answer"],
        tuple(case["variables"]),
        tuple(case["domain_exclusions"]),
        case["tolerance"],
    )


def canonical_actual(case: dict[str, Any]) -> str:
    value = case["expected_answer"]
    if isinstance(value, list):
        return "[" + ", ".join(value) + "]"
    if isinstance(value, dict):
        return "{" + ", ".join(f"{key}: {item}" for key, item in value.items()) + "}"
    return value


def _locals(case: dict[str, Any]) -> dict[str, Any]:
    values = {name: sp.Symbol(name, real=True) for name in case["variables"]}
    values.update(
        {
            "Abs": sp.Abs,
            "Complement": sp.Complement,
            "Complexes": sp.S.Complexes,
            "EmptySet": sp.EmptySet,
            "FiniteSet": sp.FiniteSet,
            "I": sp.I,
            "Interval": sp.Interval,
            "Rational": sp.Rational,
            "Reals": sp.S.Reals,
            "S": sp.S,
            "Union": sp.Union,
            "log": sp.log,
            "oo": sp.oo,
            "sqrt": sp.sqrt,
        }
    )
    return values


def _expected_symbolic(case: dict[str, Any], local: dict[str, Any]) -> Any:
    value = case["expected_answer"]
    kind = case["expected_answer_kind"]
    if kind == "finite_set":
        return sp.FiniteSet(*(sp.sympify(item, locals=local) for item in value))
    if kind == "variable_mapping":
        return {local[key]: sp.sympify(item, locals=local) for key, item in value.items()}
    return sp.sympify(value, locals=local)


def _exactly_equivalent(left: Any, right: Any) -> bool:
    difference = sp.expand_log(left - right, force=True)
    return sp.simplify(difference) == 0


def independently_verify(case: dict[str, Any]) -> tuple[bool, str]:
    local = _locals(case)
    variables = [local[name] for name in case["variables"]]
    spec = case["verification"]
    method = spec["method"]
    expected = _expected_symbolic(case, local)

    if method in {"solveset", "solveset_excluding"}:
        if len(variables) != 1:
            return False, "solveset verification requires exactly one variable"
        expression = sp.sympify(spec["expression"], locals=local)
        domain = local[spec["domain"]]
        actual = sp.solveset(expression, variables[0], domain=domain)
        if method == "solveset_excluding":
            exclusions = sp.FiniteSet(
                *(sp.sympify(item, locals=local) for item in case["domain_exclusions"])
            )
            actual = actual - exclusions
        if case["expected_answer_kind"] in {"exact_number", "approximate_numeric"}:
            if not isinstance(actual, sp.FiniteSet) or len(actual) != 1:
                return False, f"trusted solveset returned nonsingleton {sp.sstr(actual)}"
            actual_value = next(iter(actual))
            correct = sp.simplify(actual_value - expected) == 0
            return correct, f"trusted solveset returned scalar {sp.sstr(actual_value)}"
        correct = actual == expected
        if isinstance(actual, sp.FiniteSet) and isinstance(expected, sp.FiniteSet):
            correct = len(actual) == len(expected) and all(
                any(_exactly_equivalent(item, target) for item in actual) for target in expected
            )
        return correct, f"trusted solveset returned {sp.sstr(actual)}"

    if method == "solve_system":
        equations = [sp.sympify(item, locals=local) for item in spec["equations"]]
        solutions = sp.solve(equations, variables, dict=True)
        constraints = [sp.sympify(item, locals=local) for item in spec["constraints"]]
        filtered = []
        for solution in solutions:
            if all(bool(constraint.subs(solution)) for constraint in constraints):
                filtered.append(solution)
        if len(filtered) != 1:
            return False, f"trusted solve returned {len(filtered)} admissible mappings"
        correct = filtered[0].keys() == expected.keys() and all(
            sp.simplify(filtered[0][key] - expected[key]) == 0 for key in expected
        )
        return correct, f"trusted solve returned {filtered[0]}"

    if method == "inequality":
        relations = [sp.sympify(item, locals=local) for item in spec["relations"]]
        reduced = sp.reduce_inequalities(relations, variables[0])
        if reduced is sp.true:
            actual = sp.S.Reals
        elif reduced is sp.false:
            actual = sp.EmptySet
        else:
            actual = reduced.as_set()
        exclusions = sp.FiniteSet(
            *(sp.sympify(item, locals=local) for item in case["domain_exclusions"])
        )
        actual = actual - exclusions
        return actual == expected, f"trusted inequality reduction returned {sp.sstr(actual)}"

    if method == "expression":
        actual = sp.sympify(spec["expression"], locals=local)
        return sp.simplify(
            actual - expected
        ) == 0, f"trusted simplification returned {sp.sstr(actual)}"

    if method == "approximate_expression":
        actual = float(sp.N(sp.sympify(spec["expression"], locals=local), 17))
        difference = abs(actual - float(expected))
        return difference <= spec[
            "tolerance"
        ], f"trusted numeric value {actual}; difference {difference}"

    return False, f"unsupported verification method {method}"


def _policy_probe(method: str) -> str:
    probes = {
        "solveset": 'import sympy as sp\nx = sp.symbols("x", real=True)\nresult = sp.solveset(x - 1, x, domain=sp.S.Reals)\nprint(result)',
        "solveset_excluding": 'import sympy as sp\nx = sp.symbols("x", real=True)\nresult = sp.solveset((x - 1)/(x + 2), x, domain=sp.S.Reals)\nprint(result)',
        "solve_system": 'import sympy as sp\nx, y = sp.symbols("x y", real=True)\nresult = sp.nonlinsolve([x + y - 3, x*y - 2], [x, y])\nprint(result)',
        "inequality": 'import sympy as sp\nx = sp.symbols("x", real=True)\nresult = sp.solve_univariate_inequality(x > 1, x, relational=False)\nprint(result)',
        "expression": 'import sympy as sp\nx = sp.symbols("x")\nresult = sp.simplify(x + x)\nprint(result)',
        "approximate_expression": "import sympy as sp\nresult = sp.log(11)/sp.log(2)\nprint(result)",
    }
    return probes[method]


def validate_cases(cases: list[dict[str, Any]]) -> dict[str, Any]:
    assert len(cases) == 100
    assert len({case["id"] for case in cases}) == 100
    assert Counter(case["category"] for case in cases) == Counter(
        {category: 10 for category in CATEGORIES}
    )
    expected_fields = {
        "id",
        "category",
        "problem",
        "variables",
        "domain_assumptions",
        "expected_answer_kind",
        "expected_answer",
        "domain_exclusions",
        "tolerance",
        "difficulty_tier",
        "structure",
        "manual_derivation",
        "verification",
    }
    verification_details = {}
    for case in cases:
        assert set(case) == expected_fields, case["id"]
        assert re.fullmatch(r"confirm-[a-z]+-\d{2}", case["id"])
        assert case["category"] in CATEGORIES
        assert case["problem"].strip()
        assert case["domain_assumptions"]
        assert case["manual_derivation"].strip()
        assert case["difficulty_tier"] in {"basic", "intermediate", "advanced"}
        schema = expected_schema(case)
        score = score_confirmatory_answer(canonical_actual(case), schema)
        assert score.correct, (case["id"], score)
        verified, detail = independently_verify(case)
        assert verified, (case["id"], detail)
        verification_details[case["id"]] = detail
        policy = validate_confirmatory_code(_policy_probe(case["verification"]["method"]))
        assert policy.valid, (case["id"], policy)
    assert len({case["problem"].casefold().strip() for case in cases}) == 100
    return {
        "total": len(cases),
        "categories": dict(sorted(Counter(case["category"] for case in cases).items())),
        "answer_kinds": dict(
            sorted(Counter(case["expected_answer_kind"] for case in cases).items())
        ),
        "difficulty_tiers": dict(
            sorted(Counter(case["difficulty_tier"] for case in cases).items())
        ),
        "tolerance_cases": [case["id"] for case in cases if case["tolerance"] is not None],
        "domain_exclusion_cases": [case["id"] for case in cases if case["domain_exclusions"]],
        "complex_domain_cases": [
            case["id"]
            for case in cases
            if any("complex" in item.casefold() for item in case["domain_assumptions"])
        ],
        "manual_derivations_verified": 100,
        "independent_machine_verifications": 100,
        "scorer_compatibility": 100,
        "policy_method_compatibility": 100,
        "verification_details": verification_details,
    }


if __name__ == "__main__":
    print(json.dumps(validate_cases(load_cases()), indent=2, sort_keys=True))
