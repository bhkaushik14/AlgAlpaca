from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import threading

from fastapi.testclient import TestClient

from codellama_algebra.demo_service import DemoGeneratedOutput, DemoPipeline
from codellama_algebra.web_api import WebRuntime, build_run_response, create_app


def generated(raw: str) -> DemoGeneratedOutput:
    return DemoGeneratedOutput("prompt", (1, 2, 3), (4, 5), raw, "eos", 0.01)


def client_for(raw: str = 'print("ANSWER:", 4)') -> TestClient:
    return TestClient(create_app(WebRuntime(generator=lambda _: generated(raw))))


def test_health_capabilities_status_examples_and_evaluation():
    client = client_for()
    assert client.get("/api/health").json()["status"] == "ok"
    capabilities = client.get("/api/capabilities").json()
    assert capabilities["mode"] == "local"
    assert capabilities["no_data_leaves_process"] is True
    assert capabilities["telemetry_enabled"] is False
    assert capabilities["max_prompt_tokens"] == 2048
    assert client.get("/api/model-status").json()["state"] == "ready"
    assert len(client.get("/api/examples").json()["examples"]) == 6
    evaluation = client.get("/api/evaluation-summary").json()
    assert evaluation["base"] == {"correct": 17, "total": 100}
    assert evaluation["original_adapter"] == {"correct": 39, "total": 100}
    assert evaluation["v2_automated"] == {"correct": 59, "total": 100}
    assert evaluation["v2_manual"] == {"correct": 71, "total": 100}
    assert evaluation["original_executable"] == 61
    assert evaluation["v2_executable"] == 85
    assert evaluation["scorer_false_negatives"] == 12
    assert sum(evaluation[key] for key in ("original_only", "v2_only", "both_correct", "both_incorrect")) == 100


def test_empty_character_limit_and_extra_fields():
    client = client_for()
    assert client.post("/api/run", json={"problem": ""}).status_code == 422
    assert client.post("/api/run", json={"problem": "x" * 2001}).status_code == 422
    assert client.post("/api/run", json={"problem": "x=1", "code": "print(1)"}).status_code == 422


def test_pipeline_response_schema_and_parsed_output():
    response = client_for().post("/api/run", json={"problem": "Solve x=4."})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["program"]["code"] == 'print("ANSWER:", 4)'
    assert data["program"]["language"] == "Python"
    assert data["output"]["parsed_value"] == "4"
    assert [stage["state"] for stage in data["pipeline"]] == ["passed"] * 7
    assert data["details"]["prompt_token_count"] == 3
    assert data["details"]["completion_token_count"] == 2


def test_extraction_syntax_policy_runtime_and_no_output_states():
    extraction = client_for("This is prose.").post("/api/run", json={"problem": "p"}).json()
    assert extraction["pipeline"][1]["state"] == "failed"
    assert extraction["pipeline"][2]["state"] == "not_reached"
    syntax = client_for("```python\nfor\n```").post("/api/run", json={"problem": "p"}).json()
    assert syntax["pipeline"][2]["state"] == "failed"
    policy = client_for("```python\nopen('x')\n```").post("/api/run", json={"problem": "p"}).json()
    assert policy["status"] == "blocked"
    assert policy["pipeline"][3]["state"] == "failed"
    runtime = client_for("print(1/0)").post("/api/run", json={"problem": "p"}).json()
    assert runtime["output"]["execution_status"] == "nonzero_exit"
    empty = client_for("x = 1").post("/api/run", json={"problem": "p"}).json()
    assert empty["status"] == "completed_with_warning"
    assert empty["pipeline"][5]["state"] == "warning"


def test_timeout_response_mapping(monkeypatch):
    pipeline = DemoPipeline(lambda _: generated("print(1)"))

    class Execution:
        status = type("S", (), {"value": "timeout"})()
        stdout = ""
        stderr = ""
        succeeded = False
        duration_seconds = 3.0
        returncode = -9
        timed_out = True
        output_truncated = False

    monkeypatch.setattr(
        "codellama_algebra.demo_service.execute_confirmatory_validated", lambda _: Execution()
    )
    response = build_run_response(pipeline.run("p"))
    assert response["status"] == "failed"
    assert response["output"]["timed_out"] is True


def test_adapter_verification_failure_is_public_safe(tmp_path: Path):
    runtime = WebRuntime(adapter_path=tmp_path, base_revision_checker=lambda: None)
    client = TestClient(create_app(runtime))
    response = client.post("/api/run", json={"problem": "Solve x=1."})
    assert response.status_code == 503
    assert response.json()["detail"] == {
        "message": "Adapter file was not found.",
        "reason_code": "adapter_weight_missing",
    }
    status = client.get("/api/model-status").json()
    assert status["state"] == "verification_failed"
    assert status["verification_state"] == "failed"
    assert status["retry_available"] is True
    assert str(tmp_path) not in response.text


def test_request_serialization():
    entered = threading.Event()
    release = threading.Event()

    def slow(_: str) -> DemoGeneratedOutput:
        entered.set()
        release.wait(2)
        return generated("print(1)")

    runtime = WebRuntime(generator=slow)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(runtime.run, "one")
        entered.wait(1)
        try:
            runtime.run("two")
        except Exception as exc:
            assert "Another local request" in str(exc)
        else:
            raise AssertionError("concurrent request was accepted")
        release.set()
        first.result()


def test_cors_restrictions_and_no_wildcard():
    client = client_for()
    allowed = client.options(
        "/api/run",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert allowed.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"
    denied = client.options(
        "/api/run",
        headers={
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert denied.status_code == 400
    assert denied.headers.get("access-control-allow-origin") is None


def test_validation_endpoint():
    client = client_for()
    assert client.post("/api/validate", json={"problem": "   "}).json()["valid"] is False
    assert client.post("/api/validate", json={"problem": "x=1"}).json()["valid"] is True


def test_document_allowlist_and_missing_document():
    client = client_for()
    docs = client.get("/api/documentation").json()["documents"]
    assert {item["id"] for item in docs} >= {
        "evaluation",
        "architecture",
        "history",
        "limitations",
        "licensing",
        "model-card",
    }
    assert client.get("/project-docs/evaluation").status_code == 200
    assert client.get("/project-docs/not-allowlisted").status_code == 404
