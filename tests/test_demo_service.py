from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import hashlib
from pathlib import Path
import threading

import pytest

from codellama_algebra.demo_service import (
    ADAPTER_CONFIG_SHA256,
    ADAPTER_WEIGHT_SHA256,
    DemoBusyError,
    DemoGeneratedOutput,
    DemoInputError,
    DemoPipeline,
    MAX_PROBLEM_CHARS,
    sanitize_display,
    verify_adapter,
)
from codellama_algebra.confirmatory import FROZEN_GENERATION_CONFIG, render_confirmatory_prompt


def output(raw: str) -> DemoGeneratedOutput:
    return DemoGeneratedOutput("prompt", (1,), (2,), raw, "eos", 0.01)


def test_empty_and_overlength_input():
    pipeline = DemoPipeline(lambda _: output("print(1)"))
    with pytest.raises(DemoInputError):
        pipeline.run("  ")
    with pytest.raises(DemoInputError):
        pipeline.run("x" * (MAX_PROBLEM_CHARS + 1))


def test_v2_adapter_identity():
    assert ADAPTER_WEIGHT_SHA256 == "a56735e268a5343a02966d3ad8513c2b4a6232b2ed97e9dcdfaa70404293215d"
    assert ADAPTER_CONFIG_SHA256 == "67625139ecb7f71fee57be953ba8070a3f2f0981691038781747aa05b602e797"
    assert (
        FROZEN_GENERATION_CONFIG["adapter_sha256"]
        == "4dfc1a875feccfdb7affd98326d63704b5cf0ec3509468ba505cd4978e5d02d3"
    )


def test_exact_frozen_prompt_construction():
    class Tokenizer:
        def apply_chat_template(self, messages, **kwargs):
            assert kwargs == {"add_generation_prompt": True, "tokenize": False}
            return repr(messages)

    rendered = render_confirmatory_prompt(Tokenizer(), "Solve 3x=12.")
    assert "You write complete executable Python programs" in rendered
    assert "Solve 3x=12." in rendered


def test_adapter_hash_verification(tmp_path: Path, monkeypatch):
    weights = tmp_path / "adapter_model.safetensors"
    config = tmp_path / "adapter_config.json"
    weights.write_bytes(b"weights")
    config.write_bytes(b"config")
    hashes = {
        weights: hashlib.sha256(b"weights").hexdigest(),
        config: hashlib.sha256(b"config").hexdigest(),
    }
    monkeypatch.setattr("codellama_algebra.demo_service.ADAPTER_WEIGHT_SHA256", hashes[weights])
    monkeypatch.setattr("codellama_algebra.demo_service.ADAPTER_CONFIG_SHA256", hashes[config])
    assert verify_adapter(tmp_path)["adapter_model.safetensors"] == hashes[weights]
    weights.write_bytes(b"changed")
    with pytest.raises(RuntimeError, match="integrity"):
        verify_adapter(tmp_path)
    assert len(ADAPTER_WEIGHT_SHA256) == len(ADAPTER_CONFIG_SHA256) == 64


def test_successful_observable_output_and_no_repair():
    calls = []

    def fake(problem):
        calls.append(problem)
        return output('print("ANSWER:", 4)')

    result = DemoPipeline(fake).run("Solve x=4.")
    assert calls == ["Solve x=4."]

    padded = "  Solve x=4.  "
    DemoPipeline(fake).run(padded)
    assert calls[-1] == padded
    assert result.execution_status == "ok"
    assert result.parsed_output == "4"
    assert result.pipeline_status == "Execution completed"


@pytest.mark.parametrize(
    "raw,status",
    [
        ("This is prose.", "not run"),
        ("```python\nfor\n```", "failed"),
        ("```python\nopen('x')\n```", "rejected"),
    ],
)
def test_extraction_syntax_and_policy_failures(raw, status):
    result = DemoPipeline(lambda _: output(raw)).run("problem")
    assert status in {result.syntax_status, result.policy_status}
    assert result.execution_status == "not_run"


def test_runtime_error_and_no_output():
    runtime = DemoPipeline(lambda _: output("print(1/0)")).run("problem")
    assert runtime.execution_status == "nonzero_exit"
    empty = DemoPipeline(lambda _: output("x = 1")).run("problem")
    assert empty.execution_status == "ok"
    assert empty.observable_status == "no_output"


def test_timeout_status(monkeypatch):
    class Execution:
        status = type("S", (), {"value": "timeout"})()
        stdout = ""
        stderr = ""
        succeeded = False
        duration_seconds = 3.0

    monkeypatch.setattr(
        "codellama_algebra.demo_service.execute_confirmatory_validated", lambda _: Execution()
    )
    result = DemoPipeline(lambda _: output("print(1)")).run("problem")
    assert result.execution_status == "timeout"


def test_stderr_and_private_path_sanitization():
    cleaned = sanitize_display('File "/home/person/private/program.py"\n/home/person/cache', 1000)
    assert "/home/" not in cleaned
    assert "<local-path>" in cleaned


def test_concurrent_request_rejected():
    entered = threading.Event()
    release = threading.Event()

    def slow(_):
        entered.set()
        release.wait(2)
        return output("print(1)")

    pipeline = DemoPipeline(slow)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(pipeline.run, "one")
        entered.wait(1)
        with pytest.raises(DemoBusyError):
            pipeline.run("two")
        release.set()
        first.result()
