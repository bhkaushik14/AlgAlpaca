import hashlib

import pytest

from codellama_algebra.compatible import parse_observable_stdout
from codellama_algebra.confirmatory_compatible import extract_confirmatory_code
from codellama_algebra.confirmatory_scoring import score_confirmatory_answer
from codellama_algebra.scoring import ExpectedAnswer


@pytest.mark.parametrize(
    ("response", "wrapper"),
    (
        ("```PyThOn\nprint(1)\n```", "explicit_python_fence"),
        ("```py\nprint(1)\n```", "python_alias_fence"),
        ("```python3\nprint(1)\n```", "python_alias_fence"),
        ("```\nprint(1)\n```", "unlabeled_markdown_fence"),
        ("<llm-code>\nprint(1)\n</llm-code>", "legacy_llm_code"),
        ("value = 1\nprint(value)", "raw_python"),
        ("solve(Eq(x + 1, 2), x)", "raw_python"),
    ),
)
def test_confirmatory_extractor_accepts_only_documented_single_programs(response, wrapper):
    result = extract_confirmatory_code(response)
    assert result.valid, result
    assert result.wrapper_type == wrapper
    assert result.code_sha256 == hashlib.sha256(result.code.encode("utf-8")).hexdigest()
    assert result.semantic_edits is False


@pytest.mark.parametrize(
    "response",
    (
        "```python\nprint(1)\n```\n```python\nprint(2)\n```",
        "<llm-code>print(1)</llm-code><llm-code>print(2)</llm-code>",
        "```python\nprint(1)\n```\n```\nprint(2)\n```",
        "<llm-code-output>print(1)</llm-code-output>",
        "Here is code: print(1)",
        "42",
        "-3/7",
        "sqrt(2)",
        "print(",
        "```python\nprint(1)\n```\n```text\nprint(2)\n```",
        "print(0)\n```python\nprint(1)\n```",
        "```javascript\nconsole.log(1)\n```",
        "```python\nprint(1)\n```\n<llm-code>",
        "The direct solution is x = 4.",
    ),
)
def test_confirmatory_extractor_rejects_ambiguous_repaired_or_nonprogram_forms(response):
    assert not extract_confirmatory_code(response).valid


def test_extraction_performs_only_wrapper_removal_line_normalization_and_outer_trim():
    response = "prose\r\n```python\r\n  value = 2\r\nprint(value)  \r\n```\r\nend"
    result = extract_confirmatory_code(response)
    assert result.valid
    assert result.code == "value = 2\nprint(value)"
    assert set(result.transformations) == {
        "removed_explicit_python_fence",
        "trimmed_outer_whitespace",
        "normalized_line_endings",
    }


def test_stdout_hierarchy_and_diagnostics():
    result = parse_observable_stdout("diagnostic\nANSWER: 5\nmore diagnostics\n")
    assert result.status == "observable"
    assert result.answer == "5"
    assert result.diagnostic_lines == ("diagnostic", "more diagnostics")


@pytest.mark.parametrize(
    ("stdout", "status", "answer"),
    (
        ("ANSWER: 3\n", "observable", "3"),
        ("{1, 4}\n", "observable", "{1, 4}"),
        ("ANSWER:\n", "malformed_answer", None),
        ("ANSWER: 1\nANSWER: 1\n", "ambiguous_stdout", None),
        ("first\nsecond\n", "ambiguous_stdout", None),
        ("\n", "no_output", None),
    ),
)
def test_stdout_conformance_cases(stdout, status, answer):
    result = parse_observable_stdout(stdout)
    assert result.status == status
    assert result.answer == answer


@pytest.mark.parametrize(
    ("actual", "expected", "correct"),
    (
        ("17", ExpectedAnswer("exact_number", "17"), True),
        ("-19", ExpectedAnswer("exact_number", "-19"), True),
        ("7/12", ExpectedAnswer("exact_number", "7/12"), True),
        ("-11/8", ExpectedAnswer("exact_number", "-11/8"), True),
        ("sqrt(8)/2", ExpectedAnswer("exact_number", "sqrt(2)"), True),
        ("sqrt(3)", ExpectedAnswer("exact_number", "sqrt(2)"), False),
        ("1.0009", ExpectedAnswer("approximate_numeric", "1", tolerance=0.001), True),
        ("1.0011", ExpectedAnswer("approximate_numeric", "1", tolerance=0.001), False),
        ("[4]", ExpectedAnswer("finite_set", ["4"], ("x",)), True),
        ("[-2, 5, 9]", ExpectedAnswer("finite_set", ["9", "-2", "5"], ("x",)), True),
        ("[5, -2, 5, 9]", ExpectedAnswer("finite_set", ["-2", "5", "9"], ("x",)), True),
        ("{y: 3, x: -1}", ExpectedAnswer("variable_mapping", {"x": "-1", "y": "3"}, ("x", "y")), True),
        ("{x: -1, y: 4}", ExpectedAnswer("variable_mapping", {"x": "-1", "y": "3"}, ("x", "y")), False),
        ("x**2 + 2*x + 1", ExpectedAnswer("symbolic_expression", "(x + 1)**2", ("x",)), True),
        ("x**2 + 2*x - 1", ExpectedAnswer("symbolic_expression", "(x + 1)**2", ("x",)), False),
        ("Interval.open(-4, 7)", ExpectedAnswer("interval_set", "Interval.open(-4, 7)", ("x",)), True),
        ("Interval(-4, 7)", ExpectedAnswer("interval_set", "Interval(-4, 7)", ("x",)), True),
        ("Interval.Lopen(-4, 7)", ExpectedAnswer("interval_set", "Interval.Lopen(-4, 7)", ("x",)), True),
        ("Interval.open(2, oo)", ExpectedAnswer("interval_set", "Interval.open(2, oo)", ("x",)), True),
        ("Union(Interval(3, oo), Interval(-oo, -2))", ExpectedAnswer("interval_set", "Union(Interval(-oo, -2), Interval(3, oo))", ("x",)), True),
        ("x >= 6", ExpectedAnswer("interval_set", "Interval(6, oo)", ("x",)), True),
        ("EmptySet", ExpectedAnswer("interval_set", "EmptySet", ("x",)), True),
        ("Reals", ExpectedAnswer("interval_set", "Interval(-oo, oo)", ("x",)), True),
        ("S.Reals", ExpectedAnswer("interval_set", "Reals", ("x",)), True),
        ("Interval(-oo, oo)", ExpectedAnswer("interval_set", "Interval(-oo, oo)", ("x",)), True),
        ("[-I, I]", ExpectedAnswer("finite_set", ["I", "-I"], ("x",)), True),
        ("[7/2]", ExpectedAnswer("finite_set", ["7/2"], ("x",), ("2",)), True),
        ("[2, 7/2]", ExpectedAnswer("finite_set", ["7/2"], ("x",), ("2",)), False),
        ("[-sqrt(3), sqrt(3)]", ExpectedAnswer("finite_set", ["sqrt(3)", "-sqrt(3)"], ("x",)), True),
        ("[3/4]", ExpectedAnswer("finite_set", ["3/4"], ("x",)), True),
    ),
)
def test_scorer_conformance_matrix(actual, expected, correct):
    result = score_confirmatory_answer(actual, expected)
    assert result.correct is correct, result


def test_raw_expression_without_print_has_no_observable_credit():
    extraction = extract_confirmatory_code("solve(Eq(x + 1, 2), x)")
    assert extraction.valid
    assert parse_observable_stdout("").status == "no_output"
