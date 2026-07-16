from __future__ import annotations

import pytest

from codellama_algebra.presentation import (
    GENERIC_RUNTIME_ERROR,
    MAX_ERROR_SUMMARY,
    numeric_display,
    summarize_runtime_error,
)


CUBIC_EXACT = (
    "[-9/((-1/2 - sqrt(3)*I/2)*(27*sqrt(253)/2 + 513/2)**(1/3)) "
    "- (-1/2 - sqrt(3)*I/2)*(27*sqrt(253)/2 + 513/2)**(1/3)/3, "
    "-(-1/2 + sqrt(3)*I/2)*(27*sqrt(253)/2 + 513/2)**(1/3)/3 "
    "- 9/((-1/2 + sqrt(3)*I/2)*(27*sqrt(253)/2 + 513/2)**(1/3)), "
    "-(27*sqrt(253)/2 + 513/2)**(1/3)/3 "
    "- 9/(27*sqrt(253)/2 + 513/2)**(1/3)]"
)


def test_cubic_real_domain_display_is_exactly_requested_value():
    display = numeric_display(
        CUBIC_EXACT, "Solve over the real numbers: r^3 - 9r + 19 = 0."
    )
    assert display.kind == "approximate"
    assert display.value == "[-3.750]"


def test_non_real_domain_retains_complex_roots():
    display = numeric_display(CUBIC_EXACT, "Solve r^3 - 9r + 19 = 0.")
    assert display.kind == "approximate"
    assert display.value == "[1.875 + 1.245i, 1.875 - 1.245i, -3.750]"


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("2", "2"),
        ("2.5", "2.500"),
        ("-0.00001", "0"),
        ("[1, Rational(5, 2)]", "[1, 2.500]"),
        ("(1, sqrt(2))", "(1, 1.414)"),
        ("{sqrt(2), 1}", "{1, 1.414}"),
        ("{answer: sqrt(2)}", "{answer: 1.414}"),
        ("1 + 1e-12*I", "1"),
    ],
)
def test_numeric_formatting_rules(source: str, expected: str):
    display = numeric_display(source, "Find the real solutions.")
    assert display.value == expected


@pytest.mark.parametrize(
    "source",
    [
        "__import__('os').system('id')",
        "(1).__class__",
        "open('/tmp/x')",
        "[x for x in range(3)]",
        "lambda: 1",
        "sqrt(2, evaluate=False)",
        "float('nan')",
    ],
)
def test_unapproved_or_executable_forms_fall_back_without_execution(source: str):
    display = numeric_display(source, "problem")
    assert display.kind == "exact"
    assert display.value == source


def test_real_filter_with_no_remaining_values_falls_back_to_exact():
    source = "[1 + I]"
    assert numeric_display(source, "Find every real root.").value == source


def test_runtime_error_summary_removes_traceback_ansi_and_paths():
    stderr = (
        "\x1b[31mTraceback (most recent call last):\x1b[0m\n"
        '  File "/home/private-user/.cache/program.py", line 2, in <module>\n'
        "    print(1 / 0)\n"
        "ZeroDivisionError: division by zero\n"
    )
    summary = summarize_runtime_error(stderr)
    assert summary == "ZeroDivisionError: division by zero"
    assert "Traceback" not in summary
    assert "/home/" not in summary
    assert "private-user" not in summary


def test_runtime_error_summary_is_bounded_and_has_safe_fallback():
    summary = summarize_runtime_error("ValueError: " + "x" * 1000)
    assert len(summary) <= MAX_ERROR_SUMMARY
    assert summary.endswith("…")
    assert summarize_runtime_error("Traceback (most recent call last):\nunsafe echo") == (
        GENERIC_RUNTIME_ERROR
    )
    assert summarize_runtime_error("RuntimeError: token=secret-value") == GENERIC_RUNTIME_ERROR
    assert summarize_runtime_error("RuntimeError: username alice on hostname localbox") == (
        GENERIC_RUNTIME_ERROR
    )
