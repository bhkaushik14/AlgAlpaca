from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import threading

from fastapi.testclient import TestClient
import pytest

import codellama_algebra.web_api as web_api
from codellama_algebra.demo_service import DemoGeneratedOutput
from codellama_algebra.web_api import (
    VerificationBusyError,
    VerificationFailure,
    WebRuntime,
    create_app,
    verify_web_adapter,
)


def adapter_config() -> bytes:
    return json.dumps(
        {
            "base_model_name_or_path": web_api.BASE_MODEL_ID,
            "peft_type": "LORA",
            "task_type": "CAUSAL_LM",
            "r": 16,
            "lora_alpha": 32,
            "lora_dropout": 0.05,
            "target_modules": [
                "q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"
            ],
        },
        sort_keys=True,
    ).encode()


def install_adapter(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    weights: bytes = b"verified-weights",
    config: bytes | None = None,
) -> Path:
    config = adapter_config() if config is None else config
    (tmp_path / "adapter_model.safetensors").write_bytes(weights)
    (tmp_path / "adapter_config.json").write_bytes(config)
    monkeypatch.setattr(web_api, "ADAPTER_WEIGHT_BYTES", len(weights))
    monkeypatch.setattr(web_api, "ADAPTER_CONFIG_BYTES", len(config))
    monkeypatch.setattr(web_api, "ADAPTER_WEIGHT_SHA256", hashlib.sha256(weights).hexdigest())
    monkeypatch.setattr(web_api, "ADAPTER_CONFIG_SHA256", hashlib.sha256(config).hexdigest())
    return tmp_path


def generated(raw: str = 'print("ANSWER:", 4)') -> DemoGeneratedOutput:
    return DemoGeneratedOutput("prompt", (1, 2), (3, 4), raw, "eos", 0.01)


def reason(exc: pytest.ExceptionInfo[VerificationFailure]) -> str:
    return exc.value.reason_code


def test_adapter_path_not_configured():
    status = WebRuntime().model_status()
    assert status["verification_state"] == "unconfigured"
    assert status["reason_code"] == "adapter_path_not_configured"
    assert status["retry_available"] is True


def test_adapter_directory_unavailable(tmp_path: Path):
    with pytest.raises(VerificationFailure) as caught:
        verify_web_adapter(tmp_path / "missing")
    assert reason(caught) == "adapter_directory_unavailable"


def test_weight_file_missing(tmp_path: Path):
    with pytest.raises(VerificationFailure) as caught:
        verify_web_adapter(tmp_path)
    assert reason(caught) == "adapter_weight_missing"


def test_configuration_file_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    weights = b"weights"
    (tmp_path / "adapter_model.safetensors").write_bytes(weights)
    monkeypatch.setattr(web_api, "ADAPTER_WEIGHT_BYTES", len(weights))
    monkeypatch.setattr(web_api, "ADAPTER_WEIGHT_SHA256", hashlib.sha256(weights).hexdigest())
    with pytest.raises(VerificationFailure) as caught:
        verify_web_adapter(tmp_path)
    assert reason(caught) == "adapter_config_missing"


def test_weight_size_mismatch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    install_adapter(tmp_path, monkeypatch)
    monkeypatch.setattr(web_api, "ADAPTER_WEIGHT_BYTES", 999)
    with pytest.raises(VerificationFailure) as caught:
        verify_web_adapter(tmp_path)
    assert reason(caught) == "adapter_weight_size_mismatch"


def test_configuration_size_mismatch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    install_adapter(tmp_path, monkeypatch)
    monkeypatch.setattr(web_api, "ADAPTER_CONFIG_BYTES", 999)
    with pytest.raises(VerificationFailure) as caught:
        verify_web_adapter(tmp_path)
    assert reason(caught) == "adapter_config_size_mismatch"


def test_weight_hash_mismatch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    install_adapter(tmp_path, monkeypatch)
    monkeypatch.setattr(web_api, "ADAPTER_WEIGHT_SHA256", "0" * 64)
    with pytest.raises(VerificationFailure) as caught:
        verify_web_adapter(tmp_path)
    assert reason(caught) == "adapter_weight_hash_mismatch"


def test_configuration_hash_mismatch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    install_adapter(tmp_path, monkeypatch)
    monkeypatch.setattr(web_api, "ADAPTER_CONFIG_SHA256", "0" * 64)
    with pytest.raises(VerificationFailure) as caught:
        verify_web_adapter(tmp_path)
    assert reason(caught) == "adapter_config_hash_mismatch"


def test_correct_files_and_base_metadata_verify_successfully(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    adapter = install_adapter(tmp_path, monkeypatch)
    runtime = WebRuntime(adapter_path=adapter, base_revision_checker=lambda: None)
    status = runtime.model_status()
    assert status["verification_state"] == "ready"
    assert status["load_state"] == "not_loaded"
    assert status["reason_code"] == ""


def test_base_revision_unavailable_is_structured(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    adapter = install_adapter(tmp_path, monkeypatch)

    def missing():
        raise VerificationFailure("base_revision_unavailable")

    status = WebRuntime(adapter_path=adapter, base_revision_checker=missing).model_status()
    assert status["verification_state"] == "failed"
    assert status["reason_code"] == "base_revision_unavailable"


def test_no_fallback_adapter_is_selected(tmp_path: Path):
    seen: list[Path] = []

    def verifier(path: Path):
        seen.append(path)
        raise VerificationFailure("adapter_weight_missing")

    runtime = WebRuntime(
        adapter_path=tmp_path / "configured",
        adapter_verifier=verifier,
        base_revision_checker=lambda: None,
    )
    assert runtime.model_status()["verification_state"] == "failed"
    assert seen == [tmp_path / "configured"]


def test_no_private_path_appears_in_status_verify_or_run(tmp_path: Path):
    runtime = WebRuntime(
        adapter_path=tmp_path / "private-adapter",
        adapter_verifier=lambda _: (_ for _ in ()).throw(
            VerificationFailure("adapter_directory_unavailable")
        ),
        base_revision_checker=lambda: None,
    )
    client = TestClient(create_app(runtime))
    responses = [
        client.get("/api/model-status"),
        client.post("/api/model/verify"),
        client.post("/api/run", json={"problem": "Solve x=1."}),
    ]
    assert all(str(tmp_path) not in response.text for response in responses)
    assert all("Traceback" not in response.text for response in responses)


def test_failed_status_can_retry_and_success_changes_state_to_ready(tmp_path: Path):
    calls = 0

    def verifier(_: Path):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise VerificationFailure("adapter_weight_missing")
        return {}

    runtime = WebRuntime(
        adapter_path=tmp_path,
        adapter_verifier=verifier,
        base_revision_checker=lambda: None,
    )
    assert runtime.model_status()["verification_state"] == "failed"
    response = TestClient(create_app(runtime)).post("/api/model/verify")
    assert response.status_code == 200
    assert response.json()["verification_state"] == "ready"
    assert runtime.generation_enabled is True
    assert calls == 2


def test_concurrent_retry_attempts_are_controlled(tmp_path: Path):
    entered = threading.Event()
    release = threading.Event()

    def verifier(_: Path):
        entered.set()
        release.wait(2)
        return {}

    runtime = WebRuntime(
        adapter_path=tmp_path,
        adapter_verifier=verifier,
        base_revision_checker=lambda: None,
        verify_on_init=False,
    )
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(runtime.verify)
        assert entered.wait(1)
        with pytest.raises(VerificationBusyError):
            runtime.verify()
        release.set()
        assert first.result()["verification_state"] == "ready"


def test_verification_lock_is_released_after_exception(tmp_path: Path):
    calls = 0

    def verifier(_: Path):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise MemoryError("private internal detail")
        return {}

    runtime = WebRuntime(
        adapter_path=tmp_path,
        adapter_verifier=verifier,
        base_revision_checker=lambda: None,
        verify_on_init=False,
    )
    assert runtime.verify()["verification_state"] == "failed"
    assert runtime._verification_lock.locked() is False
    assert runtime.verify()["verification_state"] == "ready"


def verified_runtime(tmp_path: Path) -> WebRuntime:
    return WebRuntime(
        adapter_path=tmp_path,
        adapter_verifier=lambda _: {},
        base_revision_checker=lambda: None,
    )


def test_model_load_failure_releases_all_locks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    runtime = verified_runtime(tmp_path)
    monkeypatch.setattr(web_api, "get_real_generator", lambda _: (_ for _ in ()).throw(RuntimeError("private")))
    with pytest.raises(RuntimeError):
        runtime.run("problem")
    assert runtime._request_lock.locked() is False
    assert runtime._model_load_lock.locked() is False
    assert runtime.model_status()["load_state"] == "load_failed"


def test_generation_exception_releases_request_lock_and_allows_later_request():
    calls = 0

    def provider(_: str):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("generation failed")
        return generated()

    runtime = WebRuntime(generator=provider)
    with pytest.raises(RuntimeError):
        runtime.run("problem")
    assert runtime._request_lock.locked() is False
    assert runtime.model_status()["verification_state"] == "ready"
    assert runtime.run("problem").parsed_output == "4"


def test_extraction_exception_releases_request_lock(monkeypatch: pytest.MonkeyPatch):
    runtime = WebRuntime(generator=lambda _: generated())
    monkeypatch.setattr(
        "codellama_algebra.demo_service.extract_confirmatory_code",
        lambda _: (_ for _ in ()).throw(RuntimeError("extract")),
    )
    with pytest.raises(RuntimeError):
        runtime.run("problem")
    assert runtime._request_lock.locked() is False


def test_sandbox_exception_releases_request_lock(monkeypatch: pytest.MonkeyPatch):
    runtime = WebRuntime(generator=lambda _: generated())
    monkeypatch.setattr(
        "codellama_algebra.demo_service.execute_confirmatory_validated",
        lambda _: (_ for _ in ()).throw(RuntimeError("sandbox")),
    )
    with pytest.raises(RuntimeError):
        runtime.run("problem")
    assert runtime._request_lock.locked() is False


def test_response_serialization_exception_releases_request_lock(monkeypatch: pytest.MonkeyPatch):
    runtime = WebRuntime(generator=lambda _: generated())
    monkeypatch.setattr(
        web_api,
        "build_run_response",
        lambda _: (_ for _ in ()).throw(RuntimeError("serialization")),
    )
    client = TestClient(create_app(runtime), raise_server_exceptions=False)
    response = client.post("/api/run", json={"problem": "problem"})
    assert response.status_code == 500
    assert runtime._request_lock.locked() is False


def test_verification_failure_blocks_generation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    runtime = WebRuntime(
        adapter_path=tmp_path,
        adapter_verifier=lambda _: (_ for _ in ()).throw(
            VerificationFailure("adapter_weight_hash_mismatch")
        ),
        base_revision_checker=lambda: None,
    )
    called = False

    def loader(_: Path):
        nonlocal called
        called = True

    monkeypatch.setattr(web_api, "get_real_generator", loader)
    with pytest.raises(VerificationFailure):
        runtime.run("problem")
    assert called is False
    assert runtime._request_lock.locked() is False


def test_normal_model_response_failure_does_not_change_verified_status():
    runtime = WebRuntime(generator=lambda _: generated("This is prose."))
    result = runtime.run("problem")
    assert result.execution_status == "not_run"
    assert runtime.model_status()["verification_state"] == "ready"


def test_concurrent_generation_remains_serialized():
    entered = threading.Event()
    release = threading.Event()

    def slow(_: str):
        entered.set()
        release.wait(2)
        return generated()

    runtime = WebRuntime(generator=slow)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(runtime.run, "one")
        assert entered.wait(1)
        with pytest.raises(Exception, match="Another local request"):
            runtime.run("two")
        release.set()
        first.result()
    assert runtime._request_lock.locked() is False
