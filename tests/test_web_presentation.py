from __future__ import annotations

from codellama_algebra.demo_service import DemoGeneratedOutput, DemoPipeline
from codellama_algebra.presentation import GENERIC_RUNTIME_ERROR
from codellama_algebra.web_api import build_run_response


def generated(raw: str) -> DemoGeneratedOutput:
    return DemoGeneratedOutput("prompt", (1,), (2,), raw, "eos", 0.01)


def test_runtime_failure_response_retains_code_stderr_and_safe_summary():
    result = DemoPipeline(lambda _: generated("print(1 / 0)")).run("problem")
    response = build_run_response(result, "problem")
    assert response["program"]["code"] == "print(1 / 0)"
    assert response["output"]["execution_status"] == "nonzero_exit"
    assert "ZeroDivisionError" in response["output"]["stderr"]
    assert response["output"]["error_summary"] == "ZeroDivisionError: division by zero"
    assert "Traceback" not in response["output"]["error_summary"]


def test_syntax_failure_retains_extracted_source_and_is_not_runtime_exit():
    result = DemoPipeline(lambda _: generated("```python\nfor\n```")).run("problem")
    response = build_run_response(result, "problem")
    assert response["program"]["code"] == "for"
    assert response["details"]["syntax_result"] == "failed"
    assert response["output"]["execution_status"] == "not_run"
    assert response["output"]["error_summary"] == (
        "The generated program contains invalid Python syntax."
    )


def test_unsafe_or_empty_runtime_stderr_uses_generic_summary(monkeypatch):
    pipeline = DemoPipeline(lambda _: generated("print(1)"))

    class Execution:
        status = type("S", (), {"value": "nonzero_exit"})()
        stdout = ""
        stderr = "Traceback (most recent call last):\nsecret token=value"
        succeeded = False
        duration_seconds = 0.1
        returncode = 1
        timed_out = False
        output_truncated = False

    monkeypatch.setattr(
        "codellama_algebra.demo_service.execute_confirmatory_validated", lambda _: Execution()
    )
    response = build_run_response(pipeline.run("problem"), "problem")
    assert response["output"]["error_summary"] == GENERIC_RUNTIME_ERROR


def test_display_fields_do_not_change_stdout_or_parsed_value(monkeypatch):
    result = DemoPipeline(lambda _: generated('print("ANSWER:", 4)')).run("problem")
    response = build_run_response(result, "problem")
    assert response["output"]["stdout"] == result.stdout
    assert response["output"]["parsed_value"] == result.parsed_output == "4"
    assert response["output"]["display_value"] == "4"
    assert response["output"]["display_kind"] == "exact"

    monkeypatch.setattr(
        "codellama_algebra.web_api.numeric_display",
        lambda *_: (_ for _ in ()).throw(RuntimeError("presentation failure")),
    )
    fallback = build_run_response(result, "problem")
    assert fallback["output"]["stdout"] == result.stdout
    assert fallback["output"]["parsed_value"] == result.parsed_output
