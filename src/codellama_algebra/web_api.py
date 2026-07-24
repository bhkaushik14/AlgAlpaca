"""Local-only FastAPI boundary for the polished React workbench."""

from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import json
import os
from pathlib import Path
import threading
import time
from typing import Any, Callable

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from .confirmatory import FROZEN_GENERATION_CONFIG, PROMPT_VERSION
from .demo_service import (
    ADAPTER_CONFIG_SHA256,
    ADAPTER_WEIGHT_SHA256,
    DemoBusyError,
    DemoInputError,
    DemoPipeline,
    DemoResult,
    MAX_PROBLEM_CHARS,
    get_real_generator,
    sanitize_display,
)
from .model import BASE_MODEL_ID, BASE_MODEL_REVISION
from .presentation import DisplayResult, SYNTAX_ERROR_SUMMARY, numeric_display, summarize_runtime_error

PACKAGE_VERSION = "0.1.0.dev0"
ADAPTER_ENV = "CODELLAMA_ALGEBRA_ADAPTER_PATH"
MODEL_LABEL = "CodeLlama-7B-Instruct + AlgAlpaca v2 QLoRA"
ADAPTER_WEIGHT_BYTES = 159_967_880
ADAPTER_CONFIG_BYTES = 737
VERIFICATION_MESSAGES = {
    "adapter_path_not_configured": "Adapter path is not configured.",
    "adapter_directory_unavailable": "Adapter directory is unavailable.",
    "adapter_weight_missing": "Adapter file was not found.",
    "adapter_config_missing": "Adapter configuration was not found.",
    "adapter_weight_size_mismatch": "Adapter weight size did not match.",
    "adapter_config_size_mismatch": "Adapter configuration size did not match.",
    "adapter_weight_hash_mismatch": "Adapter weight hash did not match.",
    "adapter_config_hash_mismatch": "Adapter configuration hash did not match.",
    "adapter_config_incompatible": "Adapter configuration is incompatible.",
    "base_revision_unavailable": "Required base-model revision is unavailable.",
    "model_load_failed": "Model loading failed.",
    "verification_failed": "The adapter could not be verified.",
}
ALLOWED_ORIGINS = (
    "http://127.0.0.1:5173",
    "http://localhost:5173",
    "http://127.0.0.1:8000",
)
PUBLIC_ERROR = "Local model service unavailable. Check the local adapter and base-model cache."
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SUMMARY_PATH = PROJECT_ROOT / "evaluation/summary.json"
FRONTEND_DIST = PROJECT_ROOT / "frontend/dist"
DOCS = {
    "evaluation": ("Evaluation", "evaluation/README.md"),
    "architecture": ("Architecture", "docs/architecture.md"),
    "history": ("History", "docs/history.md"),
    "limitations": ("Limitations", "docs/limitations.md"),
    "licensing": ("Licensing", "docs/licensing.md"),
    "model-card": ("Model Card", "MODEL_CARD.md"),
}
EXAMPLES = (
    {
        "id": "linear-ticket-total",
        "category": "Linear equation",
        "title": "Ticket total",
        "problem": "A service charge of 9 dollars plus 4 dollars per ticket totals 41 dollars. Find the number of tickets.",
    },
    {
        "id": "quadratic-garden",
        "category": "Quadratic equation",
        "title": "Garden dimensions",
        "problem": "Solve over the real numbers: r^2 - 9r + 14 = 0.",
    },
    {
        "id": "system-market",
        "category": "System of equations",
        "title": "Market quantities",
        "problem": "Solve over the real numbers: 3m + 2n = 18 and m - n = 1.",
    },
    {
        "id": "rational-rate",
        "category": "Rational equation",
        "title": "Rational rate",
        "problem": "Solve over the real numbers, excluding values that make a denominator zero: 2/(x - 1) = 3/(x + 2).",
    },
    {
        "id": "absolute-distance",
        "category": "Absolute-value equation",
        "title": "Distance from a point",
        "problem": "Solve over the real numbers: |2y - 5| = 9.",
    },
    {
        "id": "function-evaluation",
        "category": "Function evaluation",
        "title": "Evaluate a polynomial",
        "problem": "Let f(t) = 2t^3 - 5t + 1. Evaluate f(-3).",
    },
)


class RunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    problem: str = Field(min_length=1, max_length=MAX_PROBLEM_CHARS)


class VerificationFailure(RuntimeError):
    """A verification failure with a stable, public-safe reason code."""

    def __init__(self, reason_code: str) -> None:
        self.reason_code = reason_code
        self.public_message = VERIFICATION_MESSAGES.get(
            reason_code, VERIFICATION_MESSAGES["verification_failed"]
        )
        super().__init__(self.public_message)


class VerificationBusyError(RuntimeError):
    """Another verification attempt owns the verification lock."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_web_adapter(adapter_path: Path) -> dict[str, str]:
    """Verify the exact v2 adapter without path discovery or model loading."""

    if adapter_path.is_symlink() or not adapter_path.is_dir():
        raise VerificationFailure("adapter_directory_unavailable")
    specifications = (
        (
            "adapter_model.safetensors",
            ADAPTER_WEIGHT_BYTES,
            ADAPTER_WEIGHT_SHA256,
            "adapter_weight_missing",
            "adapter_weight_size_mismatch",
            "adapter_weight_hash_mismatch",
        ),
        (
            "adapter_config.json",
            ADAPTER_CONFIG_BYTES,
            ADAPTER_CONFIG_SHA256,
            "adapter_config_missing",
            "adapter_config_size_mismatch",
            "adapter_config_hash_mismatch",
        ),
    )
    verified: dict[str, str] = {}
    for name, expected_bytes, expected_hash, missing, wrong_size, wrong_hash in specifications:
        artifact = adapter_path / name
        if artifact.is_symlink() or not artifact.is_file():
            raise VerificationFailure(missing)
        if artifact.stat().st_size != expected_bytes:
            raise VerificationFailure(wrong_size)
        if _sha256_file(artifact) != expected_hash:
            raise VerificationFailure(wrong_hash)
        verified[name] = expected_hash

    try:
        config = json.loads((adapter_path / "adapter_config.json").read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise VerificationFailure("adapter_config_incompatible") from None
    required = {
        "base_model_name_or_path": BASE_MODEL_ID,
        "peft_type": "LORA",
        "task_type": "CAUSAL_LM",
        "r": 16,
        "lora_alpha": 32,
        "lora_dropout": 0.05,
    }
    expected_targets = {
        "q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"
    }
    if any(config.get(key) != value for key, value in required.items()) or set(
        config.get("target_modules", [])
    ) != expected_targets:
        raise VerificationFailure("adapter_config_incompatible")
    return verified


def verify_local_base_revision() -> None:
    """Confirm frozen base metadata is locally available without loading weights."""

    try:
        from transformers import AutoConfig

        AutoConfig.from_pretrained(
            BASE_MODEL_ID,
            revision=BASE_MODEL_REVISION,
            local_files_only=True,
        )
    except (OSError, RuntimeError, ValueError):
        raise VerificationFailure("base_revision_unavailable") from None


@dataclass
class RuntimeState:
    verification_state: str
    load_state: str
    reason_code: str
    message: str


class WebRuntime:
    """Own one verified lazy local model and serialize verification, loading, and requests."""

    def __init__(
        self,
        *,
        adapter_path: Path | None = None,
        generator: Callable[[str], Any] | None = None,
        execution_enabled: bool = True,
        adapter_verifier: Callable[[Path], dict[str, str]] = verify_web_adapter,
        base_revision_checker: Callable[[], None] = verify_local_base_revision,
        verify_on_init: bool = True,
    ) -> None:
        self.adapter_path = adapter_path
        self.generator = generator
        self.execution_enabled = execution_enabled
        self._adapter_verifier = adapter_verifier
        self._base_revision_checker = base_revision_checker
        self._pipeline = DemoPipeline(generator) if generator is not None else None
        self._state_lock = threading.Lock()
        self._request_lock = threading.Lock()
        self._verification_lock = threading.Lock()
        self._model_load_lock = threading.Lock()
        if generator is not None:
            self.state = RuntimeState("ready", "loaded", "", "Model provider is ready.")
        elif adapter_path is None:
            self.state = RuntimeState(
                "unconfigured",
                "not_loaded",
                "adapter_path_not_configured",
                VERIFICATION_MESSAGES["adapter_path_not_configured"],
            )
        else:
            self.state = RuntimeState("verifying", "not_loaded", "", "Verifying adapter…")
            if verify_on_init:
                self.verify()

    @property
    def generation_enabled(self) -> bool:
        with self._state_lock:
            return self.state.verification_state == "ready"

    def _legacy_state(self, state: RuntimeState) -> str:
        if state.verification_state == "failed":
            return "verification_failed"
        if state.verification_state == "unconfigured":
            return "unavailable"
        if state.verification_state == "verifying" or state.load_state == "loading":
            return "loading"
        if state.load_state == "loaded":
            return "ready"
        if state.load_state == "load_failed":
            return "unavailable"
        return "not_loaded"

    def model_status(self) -> dict[str, Any]:
        with self._state_lock:
            state = replace(self.state)
        adapter_verification = {
            "unconfigured": "not_checked",
            "verifying": "checking",
            "ready": "verified",
            "failed": "failed",
        }[state.verification_state]
        return {
            "state": self._legacy_state(state),
            "adapter_verification": adapter_verification,
            "verification_state": state.verification_state,
            "load_state": state.load_state,
            "retry_available": (
                not self._verification_lock.locked() and state.load_state != "loading"
            ),
            "reason_code": state.reason_code,
            "request_busy": self._request_lock.locked(),
            "message": state.message,
            "model": MODEL_LABEL,
            "base_model": BASE_MODEL_ID,
            "base_revision": BASE_MODEL_REVISION,
            "adapter_hash": ADAPTER_WEIGHT_SHA256[:12],
        }

    def _replace_state(self, **changes: str) -> None:
        with self._state_lock:
            self.state = replace(self.state, **changes)

    def verify(self) -> dict[str, Any]:
        """Recompute adapter and base metadata checks without loading the model."""

        if not self._verification_lock.acquire(blocking=False):
            raise VerificationBusyError("Adapter verification is already running.")
        try:
            if self.adapter_path is None:
                self._replace_state(
                    verification_state="unconfigured",
                    reason_code="adapter_path_not_configured",
                    message=VERIFICATION_MESSAGES["adapter_path_not_configured"],
                )
                return self.model_status()
            self._replace_state(
                verification_state="verifying",
                reason_code="",
                message="Verifying adapter…",
            )
            try:
                self._adapter_verifier(self.adapter_path)
                self._base_revision_checker()
            except VerificationFailure as exc:
                self._replace_state(
                    verification_state="failed",
                    reason_code=exc.reason_code,
                    message=exc.public_message,
                )
                return self.model_status()
            except Exception:
                self._replace_state(
                    verification_state="failed",
                    reason_code="verification_failed",
                    message=VERIFICATION_MESSAGES["verification_failed"],
                )
                return self.model_status()
            load_state = "loaded" if self._pipeline is not None else "not_loaded"
            self._replace_state(
                verification_state="ready",
                load_state=load_state,
                reason_code="",
                message="Adapter and frozen base revision are verified.",
            )
            return self.model_status()
        finally:
            self._verification_lock.release()

    def _ensure_pipeline(self) -> DemoPipeline:
        if self._pipeline is not None:
            return self._pipeline
        with self._state_lock:
            state = replace(self.state)
        if state.verification_state != "ready":
            reason = state.reason_code or "verification_failed"
            raise VerificationFailure(reason)
        if not self._model_load_lock.acquire(blocking=False):
            raise DemoBusyError("The local model is already loading.")
        try:
            if self._pipeline is not None:
                return self._pipeline
            self._replace_state(load_state="loading", reason_code="", message="Loading local model.")
            try:
                generator = get_real_generator(self.adapter_path)
            except Exception:
                self._replace_state(
                    load_state="load_failed",
                    reason_code="model_load_failed",
                    message=VERIFICATION_MESSAGES["model_load_failed"],
                )
                raise RuntimeError(PUBLIC_ERROR) from None
            self.generator = generator
            self._pipeline = DemoPipeline(generator)
            self._replace_state(
                load_state="loaded", reason_code="", message="Local model and adapter are ready."
            )
            return self._pipeline
        finally:
            self._model_load_lock.release()

    def validate_problem(self, problem: str) -> dict[str, Any]:
        stripped = problem.strip()
        if not stripped:
            return {"valid": False, "message": "Enter an algebra problem.", "token_count": None}
        if len(problem) > MAX_PROBLEM_CHARS:
            return {
                "valid": False,
                "message": f"Problem exceeds the {MAX_PROBLEM_CHARS}-character limit.",
                "token_count": None,
            }
        tokenizer = getattr(getattr(self.generator, "loaded", None), "tokenizer", None)
        if tokenizer is None:
            return {"valid": True, "message": "Token count will be checked before generation.", "token_count": None}
        from .confirmatory_tokenization import build_confirmatory_model_input

        try:
            _, token_ids = build_confirmatory_model_input(
                tokenizer,
                problem,
                max_input_tokens=FROZEN_GENERATION_CONFIG["max_input_tokens"],
            )
        except ValueError as exc:
            return {"valid": False, "message": sanitize_display(str(exc), 300), "token_count": None}
        return {"valid": True, "message": "Input is within the prompt-token limit.", "token_count": len(token_ids)}

    def run(self, problem: str) -> DemoResult:
        if not self._request_lock.acquire(blocking=False):
            raise DemoBusyError("Another local request is running; wait for it to finish.")
        try:
            pipeline = self._ensure_pipeline()
            return pipeline.run(problem)
        finally:
            self._request_lock.release()


def _stage(stage_id: str, label: str, state: str, detail: str = "") -> dict[str, str]:
    return {"id": stage_id, "label": label, "state": state, "detail": detail}


def _pipeline_stages(result: DemoResult) -> list[dict[str, str]]:
    extracted = bool(result.extracted_code)
    syntax_passed = result.syntax_status == "passed"
    policy_passed = result.policy_status == "passed"
    executed = result.execution_status != "not_run"
    execution_passed = result.execution_status == "ok"
    observable = result.observable_status == "observable"
    return [
        _stage("response", "Model response received", "passed"),
        _stage(
            "extraction",
            "Code extracted",
            "passed" if extracted else "failed",
            result.wrapper_status,
        ),
        _stage(
            "syntax",
            "Python syntax validated",
            "passed" if syntax_passed else "failed" if extracted else "not_reached",
            result.validation_error_code if result.syntax_status == "failed" else "",
        ),
        _stage(
            "policy",
            "Safety policy checked",
            "passed" if policy_passed else "failed" if syntax_passed else "not_reached",
            result.validation_error_code if result.policy_status == "rejected" else "",
        ),
        _stage(
            "execution",
            "Program executed",
            "passed" if execution_passed else "failed" if executed else "not_reached",
            result.execution_status if executed else "",
        ),
        _stage(
            "observable",
            "Observable output detected",
            "passed" if observable else "warning" if execution_passed else "not_reached",
            result.observable_status if execution_passed else "",
        ),
        _stage(
            "parsed",
            "Output parsed",
            "passed" if result.parsed_output else "warning" if observable else "not_reached",
            result.observable_mode,
        ),
    ]


def build_run_response(result: DemoResult, problem: str = "") -> dict[str, Any]:
    total = result.generation_latency_seconds + result.execution_latency_seconds
    if result.policy_status == "rejected":
        status = "blocked"
        label = "Blocked"
    elif result.execution_status not in {"ok", "not_run"} or result.syntax_status == "failed":
        status = "failed"
        label = "Failed"
    elif result.execution_status == "ok" and result.observable_status == "observable":
        status = "completed"
        label = "Completed"
    else:
        status = "completed_with_warning"
        label = "Completed with warning"
    uses_sympy = bool(
        result.extracted_code
        and ("import sympy" in result.extracted_code or "from sympy" in result.extracted_code)
    )
    violations = tuple(sanitize_display(item, 300) for item in result.validation_violations)
    try:
        display = numeric_display(result.parsed_output, problem)
    except Exception:
        display = DisplayResult(
            result.parsed_output, "exact" if result.parsed_output else "none"
        )
    if result.syntax_status == "failed":
        error_summary = SYNTAX_ERROR_SUMMARY
    elif result.timed_out or result.policy_status == "rejected":
        error_summary = ""
    elif result.execution_status not in {"ok", "not_run"}:
        error_summary = summarize_runtime_error(result.stderr)
    else:
        error_summary = ""
    return {
        "status": status,
        "message": result.pipeline_status,
        "program": {
            "code": result.extracted_code,
            "language": "Python",
            "uses_sympy": uses_sympy,
            "extraction_type": result.wrapper_status,
            "sha256": result.extracted_code_sha256,
            "normalization": list(result.extraction_transformations),
            "generated_token_count": result.generated_token_count,
        },
        "output": {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "parsed_value": result.parsed_output,
            "display_value": display.value,
            "display_kind": display.kind,
            "error_summary": error_summary,
            "observable_status": result.observable_status,
            "execution_status": result.execution_status,
            "exit_status": result.returncode,
            "timed_out": result.timed_out,
            "output_truncated": result.output_truncated,
        },
        "pipeline": _pipeline_stages(result),
        "details": {
            "raw_response": result.raw_response,
            "raw_response_sha256": result.raw_response_sha256,
            "syntax_result": result.syntax_status,
            "policy_result": result.policy_status,
            "blocked_rule_category": result.validation_error_code,
            "policy_violations": list(violations),
            "prompt_version": result.prompt_version,
            "model_revision": BASE_MODEL_REVISION,
            "adapter_hash": ADAPTER_WEIGHT_SHA256[:12],
            "prompt_token_count": result.input_token_count,
            "completion_token_count": result.generated_token_count,
            "stopping_reason": result.stopping_reason,
            "generation_seconds": result.generation_latency_seconds,
            "execution_seconds": result.execution_latency_seconds,
        },
        "summary": {
            "status": label,
            "model": MODEL_LABEL,
            "total_seconds": total,
            "prompt_token_count": result.input_token_count,
            "completion_token_count": result.generated_token_count,
        },
    }


def _evaluation_summary() -> dict[str, Any]:
    data = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    base = data["conditions"]["base"]["primary_correctness"]
    original = data["conditions"]["adapter"]
    original_score = original["primary_correctness"]
    v2_automated = data["conditions"]["v2"]["primary_correctness"]
    v2_manual = data["conditions"]["v2"]["manual_correctness"]
    paired = data["paired_original_v2_automated"]
    return {
        "schema_version": data["schema_version"],
        "base": {"correct": base["numerator"], "total": base["denominator"]},
        "original_adapter": {
            "correct": original_score["numerator"],
            "total": original_score["denominator"],
        },
        "v2_automated": {"correct": v2_automated["numerator"], "total": v2_automated["denominator"]},
        "v2_manual": {"correct": v2_manual["numerator"], "total": v2_manual["denominator"]},
        "original_executable": original["executable"]["numerator"],
        "v2_executable": data["conditions"]["v2"]["executable"]["numerator"],
        "scorer_false_negatives": v2_manual["scorer_false_negatives"],
        "original_only": paired["original_only"],
        "v2_only": paired["v2_only"],
        "both_correct": paired["both_correct"],
        "both_incorrect": paired["both_incorrect"],
        "protocol": "Deterministic one-call, no-repair confirmatory protocol",
        "limitation": "Project-specific fixture; v2 still requires mathematical and code review.",
        "documentation": "/project-docs/evaluation",
    }


def create_app(runtime: WebRuntime | None = None, *, frontend_dist: Path | None = None) -> FastAPI:
    adapter_value = os.environ.get(ADAPTER_ENV)
    runtime = runtime or WebRuntime(adapter_path=Path(adapter_value) if adapter_value else None)
    app = FastAPI(
        title="AlgAlpaca local API",
        version=PACKAGE_VERSION,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.runtime = runtime
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(ALLOWED_ORIGINS),
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type"],
        max_age=600,
    )

    @app.exception_handler(Exception)
    async def unhandled_error(_: Request, exc: Exception) -> JSONResponse:
        if isinstance(exc, HTTPException):
            return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
        return JSONResponse({"detail": "The local request could not be completed."}, status_code=500)

    @app.get("/api/health")
    def health() -> dict[str, Any]:
        return {"status": "ok", "service": "algebra-to-code", "version": PACKAGE_VERSION}

    @app.get("/api/capabilities")
    def capabilities() -> dict[str, Any]:
        return {
            "mode": "local",
            "generation_enabled": runtime.generation_enabled,
            "code_execution_enabled": runtime.execution_enabled,
            "model_load_on_first_run": True,
            "no_data_leaves_process": True,
            "persistence_enabled": False,
            "telemetry_enabled": False,
            "max_problem_characters": MAX_PROBLEM_CHARS,
            "max_prompt_tokens": FROZEN_GENERATION_CONFIG["max_input_tokens"],
            "prompt_version": PROMPT_VERSION,
            "backend_version": PACKAGE_VERSION,
        }

    @app.get("/api/model-status")
    def model_status() -> dict[str, Any]:
        return runtime.model_status()

    @app.post("/api/model/verify")
    def verify_model() -> dict[str, Any]:
        try:
            return runtime.verify()
        except VerificationBusyError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from None

    @app.get("/api/examples")
    def examples() -> dict[str, Any]:
        return {"examples": list(EXAMPLES)}

    @app.get("/api/evaluation-summary")
    def evaluation_summary() -> dict[str, Any]:
        return _evaluation_summary()

    @app.get("/api/documentation")
    def documentation() -> dict[str, Any]:
        return {
            "documents": [
                {"id": doc_id, "title": title, "href": f"/project-docs/{doc_id}"}
                for doc_id, (title, _) in DOCS.items()
            ]
        }

    @app.post("/api/validate")
    def validate(payload: RunRequest) -> dict[str, Any]:
        return runtime.validate_problem(payload.problem)

    @app.post("/api/run")
    def run(payload: RunRequest) -> dict[str, Any]:
        started = time.perf_counter()
        try:
            result = runtime.run(payload.problem)
        except DemoBusyError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from None
        except VerificationFailure as exc:
            raise HTTPException(
                status_code=503,
                detail={"message": exc.public_message, "reason_code": exc.reason_code},
            ) from None
        except DemoInputError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from None
        except ValueError as exc:
            message = sanitize_display(str(exc), 300)
            if "token" not in message.casefold():
                message = "The request is not valid for the frozen local prompt."
            raise HTTPException(status_code=422, detail=message) from None
        except RuntimeError as exc:
            message = str(exc)
            if "integrity verification failed" not in message:
                message = PUBLIC_ERROR
            raise HTTPException(status_code=503, detail=message) from None
        response = build_run_response(result, payload.problem)
        response["summary"]["request_seconds"] = time.perf_counter() - started
        return response

    @app.get("/project-docs/{doc_id}", response_class=FileResponse)
    def project_doc(doc_id: str) -> FileResponse:
        if doc_id not in DOCS:
            raise HTTPException(status_code=404, detail="Document not found.")
        path = (PROJECT_ROOT / DOCS[doc_id][1]).resolve()
        if PROJECT_ROOT.resolve() not in path.parents or not path.is_file() or path.is_symlink():
            raise HTTPException(status_code=404, detail="Document not found.")
        return FileResponse(path, media_type="text/markdown", filename=path.name)

    dist = frontend_dist if frontend_dist is not None else FRONTEND_DIST
    index = dist / "index.html"
    assets = dist / "assets"
    if index.is_file() and not index.is_symlink():
        if assets.is_dir() and not assets.is_symlink():
            app.mount("/assets", StaticFiles(directory=assets), name="frontend-assets")

        @app.get("/{path:path}", response_class=FileResponse)
        def frontend(path: str) -> FileResponse:
            candidate = (dist / path).resolve()
            if dist.resolve() in candidate.parents and candidate.is_file() and not candidate.is_symlink():
                return FileResponse(candidate)
            return FileResponse(index)

    return app


app = create_app()


def main() -> None:
    import uvicorn

    uvicorn.run("codellama_algebra.web_api:app", host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    main()
