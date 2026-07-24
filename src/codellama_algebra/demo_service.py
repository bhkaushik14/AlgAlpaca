"""Local-only, one-call adapter demonstration pipeline."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
from pathlib import Path
import re
import threading
from typing import Any, Callable

from .compatible import parse_observable_stdout
from .confirmatory import FROZEN_GENERATION_CONFIG, PROMPT_VERSION
from .confirmatory_compatible import extract_confirmatory_code
from .confirmatory_sandbox import execute_confirmatory_validated
from .confirmatory_tokenization import build_confirmatory_model_input
from .confirmatory_validation import validate_confirmatory_code
from .model import ModelLoadConfig, load_model

ADAPTER_WEIGHT_SHA256 = "a56735e268a5343a02966d3ad8513c2b4a6232b2ed97e9dcdfaa70404293215d"
ADAPTER_CONFIG_SHA256 = "67625139ecb7f71fee57be953ba8070a3f2f0981691038781747aa05b602e797"
MAX_PROBLEM_CHARS = 2_000
MAX_DISPLAY_STDOUT = 8_192
MAX_DISPLAY_STDERR = 4_096
MAX_DISPLAY_RAW_RESPONSE = 16_384


class DemoInputError(ValueError):
    """A safe user-facing input failure."""


class DemoBusyError(RuntimeError):
    """A generation is already using the singleton model."""


@dataclass(frozen=True)
class DemoGeneratedOutput:
    rendered_prompt: str
    input_token_ids: tuple[int, ...]
    generated_token_ids: tuple[int, ...]
    exact_decoded_raw_output: str
    stopping_reason: str
    generation_latency_seconds: float


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_adapter(adapter_path: Path) -> dict[str, str]:
    """Verify exact regular adapter files without following symlinks."""

    if not adapter_path.is_dir() or adapter_path.is_symlink():
        raise RuntimeError("The configured adapter directory is unavailable or unsafe.")
    expected = {
        "adapter_model.safetensors": ADAPTER_WEIGHT_SHA256,
        "adapter_config.json": ADAPTER_CONFIG_SHA256,
    }
    for name, wanted in expected.items():
        path = adapter_path / name
        if not path.is_file() or path.is_symlink() or _sha256(path) != wanted:
            raise RuntimeError(f"Adapter integrity verification failed for {name}.")
    return expected


class RealAdapterGenerator:
    """One locally cached adapter/model pair using the frozen one-call generator."""

    def __init__(self, adapter_path: Path) -> None:
        verify_adapter(adapter_path)
        self.loaded = load_model(
            ModelLoadConfig(adapter_id_or_path=str(adapter_path), local_files_only=True)
        )

    def __call__(self, problem: str) -> DemoGeneratedOutput:
        import time
        import torch

        rendered, input_ids = build_confirmatory_model_input(
            self.loaded.tokenizer,
            problem,
            max_input_tokens=FROZEN_GENERATION_CONFIG["max_input_tokens"],
        )
        input_tensor = torch.tensor([input_ids], dtype=torch.long, device=self.loaded.model.device)
        attention_mask = torch.ones_like(input_tensor)
        started = time.perf_counter()
        output = self.loaded.model.generate(
            input_ids=input_tensor,
            attention_mask=attention_mask,
            max_new_tokens=FROZEN_GENERATION_CONFIG["max_new_tokens"],
            do_sample=False,
            eos_token_id=self.loaded.tokenizer.eos_token_id,
            pad_token_id=self.loaded.tokenizer.pad_token_id,
            use_cache=True,
        )
        duration = time.perf_counter() - started
        full_ids = [int(token_id) for token_id in output[0].tolist()]
        if full_ids[: len(input_ids)] != input_ids:
            raise RuntimeError("Generated tokens did not preserve the prompt prefix.")
        generated_ids = full_ids[len(input_ids) :]
        stopping = (
            "eos"
            if generated_ids and generated_ids[-1] == self.loaded.tokenizer.eos_token_id
            else "max_new_tokens"
            if len(generated_ids) >= FROZEN_GENERATION_CONFIG["max_new_tokens"]
            else "other_stopping_criterion"
        )
        raw = self.loaded.tokenizer.decode(
            generated_ids,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=False,
        )
        return DemoGeneratedOutput(
            rendered, tuple(input_ids), tuple(generated_ids), raw, stopping, duration
        )


_singleton_lock = threading.Lock()
_singletons: dict[str, RealAdapterGenerator] = {}


def get_real_generator(adapter_path: Path) -> RealAdapterGenerator:
    key = str(adapter_path.resolve())
    with _singleton_lock:
        if key not in _singletons:
            _singletons[key] = RealAdapterGenerator(adapter_path)
        return _singletons[key]


def sanitize_display(text: str, limit: int) -> str:
    """Bound output and remove absolute paths and traceback internals."""

    text = re.sub(r"(?<![\w.-])/(?:[^\s:'\"]+/)+[^\s:'\"]*", "<local-path>", text)
    text = re.sub(r'File "[^"]+"', 'File "<local-path>"', text)
    if len(text) > limit:
        return text[:limit] + "\n<display truncated>"
    return text


@dataclass(frozen=True)
class DemoResult:
    pipeline_status: str
    extracted_code: str
    stdout: str
    stderr: str
    wrapper_status: str
    syntax_status: str
    policy_status: str
    execution_status: str
    observable_status: str
    parsed_output: str
    raw_response: str
    generation_latency_seconds: float
    execution_latency_seconds: float
    prompt_version: str = PROMPT_VERSION
    input_token_count: int = 0
    generated_token_count: int = 0
    stopping_reason: str = ""
    raw_response_sha256: str = ""
    extracted_code_sha256: str = ""
    extraction_transformations: tuple[str, ...] = ()
    validation_error_code: str = ""
    validation_violations: tuple[str, ...] = ()
    observable_mode: str = ""
    returncode: int | None = None
    timed_out: bool = False
    output_truncated: bool = False


class DemoPipeline:
    """Serialize generation and run exact extracted source only after policy approval."""

    def __init__(self, generator: Callable[[str], DemoGeneratedOutput]) -> None:
        self.generator = generator
        self._generation_lock = threading.Lock()

    def run(self, problem: str) -> DemoResult:
        if not problem.strip():
            raise DemoInputError("Enter an algebra problem.")
        if len(problem) > MAX_PROBLEM_CHARS:
            raise DemoInputError(f"Problem exceeds the {MAX_PROBLEM_CHARS}-character limit.")
        if not self._generation_lock.acquire(blocking=False):
            raise DemoBusyError(
                "Another local generation is in progress; try again when it finishes."
            )
        try:
            generated = self.generator(problem)
        finally:
            self._generation_lock.release()

        extraction = extract_confirmatory_code(generated.exact_decoded_raw_output)
        validation = validate_confirmatory_code(extraction.code) if extraction.valid else None
        syntax = (
            "not run"
            if validation is None
            else "failed"
            if validation.error_code == "syntax_error"
            else "passed"
        )
        policy = (
            "not run"
            if validation is None or validation.error_code == "syntax_error"
            else "passed"
            if validation.valid
            else "rejected"
        )
        execution = (
            execute_confirmatory_validated(validation)
            if validation is not None and validation.valid
            else None
        )
        observable = (
            parse_observable_stdout(execution.stdout)
            if execution is not None and execution.succeeded
            else None
        )
        parsed = observable.answer if observable is not None and observable.answer else ""
        execution_status = execution.status.value if execution is not None else "not_run"
        pipeline_status = (
            "Execution completed"
            if execution is not None and execution.succeeded
            else "Generation completed; no approved program was executed"
            if execution is None
            else "Execution did not complete successfully"
        )
        return DemoResult(
            pipeline_status=pipeline_status,
            extracted_code=extraction.code or "",
            stdout=sanitize_display(execution.stdout if execution else "", MAX_DISPLAY_STDOUT),
            stderr=sanitize_display(execution.stderr if execution else "", MAX_DISPLAY_STDERR),
            wrapper_status=extraction.wrapper_type or extraction.error_code or "raw_python",
            syntax_status=syntax,
            policy_status=policy,
            execution_status=execution_status,
            observable_status=observable.status if observable is not None else "not_run",
            parsed_output=parsed,
            raw_response=sanitize_display(
                generated.exact_decoded_raw_output, MAX_DISPLAY_RAW_RESPONSE
            ),
            generation_latency_seconds=generated.generation_latency_seconds,
            execution_latency_seconds=execution.duration_seconds if execution else 0.0,
            input_token_count=len(generated.input_token_ids),
            generated_token_count=len(generated.generated_token_ids),
            stopping_reason=generated.stopping_reason,
            raw_response_sha256=extraction.raw_response_sha256,
            extracted_code_sha256=extraction.code_sha256 or "",
            extraction_transformations=extraction.transformations,
            validation_error_code=validation.error_code if validation else "",
            validation_violations=validation.violations if validation else (),
            observable_mode=observable.mode if observable and observable.mode else "",
            returncode=getattr(execution, "returncode", None) if execution else None,
            timed_out=bool(getattr(execution, "timed_out", False)) if execution else False,
            output_truncated=(
                bool(getattr(execution, "output_truncated", False)) if execution else False
            ),
        )


def result_dict(result: DemoResult) -> dict[str, Any]:
    return asdict(result)
