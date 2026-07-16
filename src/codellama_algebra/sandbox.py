"""Restricted subprocess execution for controlled local evaluation.

This is defense in depth around AST-approved code, not hardened multi-tenant isolation.
"""

from __future__ import annotations

import os
import resource
import selectors
import signal
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from .validation import (
    ValidationResult,
    validate_code,
    validate_code_compatible,
    validate_response,
)


class ExecutionStatus(str, Enum):
    OK = "ok"
    POLICY_FAILURE = "policy_failure"
    TIMEOUT = "timeout"
    EXCESSIVE_OUTPUT = "excessive_output"
    NONZERO_EXIT = "nonzero_exit"
    MISSING_ANSWER = "missing_answer"
    MULTIPLE_ANSWERS = "multiple_answers"
    MALFORMED_OUTPUT = "malformed_output"
    PLATFORM_ERROR = "platform_error"


@dataclass(frozen=True)
class ExecutionLimits:
    """Wall-clock and POSIX resource ceilings for one worker."""

    wall_seconds: float = 3.0
    cpu_seconds: int = 2
    memory_bytes: int = 768 * 1024 * 1024
    file_bytes: int = 1024 * 1024
    stdout_bytes: int = 8192
    stderr_bytes: int = 8192
    open_files: int = 32
    processes: int = 1


@dataclass(frozen=True)
class ExecutionResult:
    """Stage-specific subprocess outcome."""

    status: ExecutionStatus
    validation: ValidationResult | None
    returncode: int | None
    stdout: str
    stderr: str
    answer: str | None
    duration_seconds: float
    timed_out: bool = False
    output_truncated: bool = False
    message: str | None = None

    @property
    def succeeded(self) -> bool:
        return self.status is ExecutionStatus.OK


def _limit_worker(limits: ExecutionLimits) -> None:
    resource.setrlimit(resource.RLIMIT_CPU, (limits.cpu_seconds, limits.cpu_seconds))
    resource.setrlimit(resource.RLIMIT_AS, (limits.memory_bytes, limits.memory_bytes))
    resource.setrlimit(resource.RLIMIT_FSIZE, (limits.file_bytes, limits.file_bytes))
    resource.setrlimit(resource.RLIMIT_NOFILE, (limits.open_files, limits.open_files))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    if hasattr(resource, "RLIMIT_NPROC"):
        resource.setrlimit(resource.RLIMIT_NPROC, (limits.processes, limits.processes))


def _terminate_group(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def _collect_bounded(
    process: subprocess.Popen[bytes], limits: ExecutionLimits
) -> tuple[bytes, bytes, bool, bool]:
    selector = selectors.DefaultSelector()
    assert process.stdout is not None and process.stderr is not None
    selector.register(process.stdout, selectors.EVENT_READ, "stdout")
    selector.register(process.stderr, selectors.EVENT_READ, "stderr")
    chunks: dict[str, bytearray] = {"stdout": bytearray(), "stderr": bytearray()}
    caps = {"stdout": limits.stdout_bytes, "stderr": limits.stderr_bytes}
    deadline = time.monotonic() + limits.wall_seconds
    timed_out = False
    excessive = False

    while selector.get_map():
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            timed_out = True
            _terminate_group(process)
            break
        events = selector.select(timeout=min(remaining, 0.05))
        if not events and process.poll() is not None:
            events = [(key, selectors.EVENT_READ) for key in selector.get_map().values()]
        for key, _ in events:
            data = os.read(key.fileobj.fileno(), 4096)
            if not data:
                selector.unregister(key.fileobj)
                continue
            stream = key.data
            room = caps[stream] - len(chunks[stream])
            chunks[stream].extend(data[: max(room, 0)])
            if len(data) > max(room, 0):
                excessive = True
                _terminate_group(process)
                break
        if excessive:
            break

    process.wait()
    selector.close()
    process.stdout.close()
    process.stderr.close()
    return bytes(chunks["stdout"]), bytes(chunks["stderr"]), timed_out, excessive


def _execute_approved_code(
    code: str,
    limits: ExecutionLimits,
    *,
    enforce_answer_contract: bool = True,
) -> ExecutionResult:
    """Private worker primitive; callers must first obtain a valid policy result.

    The strict path keeps its original one-line ``ANSWER:`` contract. The secondary compatible
    path disables only that post-execution contract so it can retain exact stdout for a separate,
    documented observable-value parser.
    """

    started = time.monotonic()
    if os.name != "posix":
        return ExecutionResult(
            ExecutionStatus.PLATFORM_ERROR,
            None,
            None,
            "",
            "",
            None,
            0.0,
            message="POSIX resource limits are unavailable on this platform.",
        )

    with tempfile.TemporaryDirectory(prefix="algebra-eval-") as temp_dir:
        script_path = Path(temp_dir) / "program.py"
        script_path.write_text(code, encoding="utf-8")
        environment = {
            "HOME": temp_dir,
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "PATH": os.defpath,
        }
        try:
            process = subprocess.Popen(
                [sys.executable, "-I", str(script_path)],
                cwd=temp_dir,
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
                preexec_fn=lambda: _limit_worker(limits),
            )
            stdout_raw, stderr_raw, timed_out, excessive = _collect_bounded(process, limits)
        except (OSError, ValueError) as exc:
            return ExecutionResult(
                ExecutionStatus.PLATFORM_ERROR,
                None,
                None,
                "",
                "",
                None,
                time.monotonic() - started,
                message=str(exc),
            )

    stdout = stdout_raw.decode("utf-8", errors="replace")
    stderr = stderr_raw.decode("utf-8", errors="replace")
    duration = time.monotonic() - started
    if timed_out:
        return ExecutionResult(
            ExecutionStatus.TIMEOUT,
            None,
            process.returncode,
            stdout,
            stderr,
            None,
            duration,
            timed_out=True,
            message="Worker exceeded the wall-clock limit.",
        )
    if excessive:
        return ExecutionResult(
            ExecutionStatus.EXCESSIVE_OUTPUT,
            None,
            process.returncode,
            stdout,
            stderr,
            None,
            duration,
            output_truncated=True,
            message="Worker output exceeded a configured byte limit.",
        )
    if process.returncode != 0:
        return ExecutionResult(
            ExecutionStatus.NONZERO_EXIT,
            None,
            process.returncode,
            stdout,
            stderr,
            None,
            duration,
            message="Worker exited with a nonzero status.",
        )
    if not enforce_answer_contract:
        return ExecutionResult(
            ExecutionStatus.OK,
            None,
            process.returncode,
            stdout,
            stderr,
            None,
            duration,
        )

    nonempty_lines = [line.strip() for line in stdout.splitlines() if line.strip()]
    answer_lines = [line for line in nonempty_lines if line.startswith("ANSWER:")]
    if not answer_lines:
        status = ExecutionStatus.MISSING_ANSWER
        message = "Worker produced no ANSWER: line."
    elif len(answer_lines) > 1:
        status = ExecutionStatus.MULTIPLE_ANSWERS
        message = "Worker produced multiple ANSWER: lines."
    elif len(nonempty_lines) != 1:
        status = ExecutionStatus.MALFORMED_OUTPUT
        message = "Worker output must contain exactly one nonempty line."
    elif not answer_lines[0][len("ANSWER:") :].strip():
        status = ExecutionStatus.MALFORMED_OUTPUT
        message = "ANSWER: output is empty."
    else:
        status = ExecutionStatus.OK
        message = None
    answer = answer_lines[0][len("ANSWER:") :].strip() if status is ExecutionStatus.OK else None
    return ExecutionResult(
        status,
        None,
        process.returncode,
        stdout,
        stderr,
        answer,
        duration,
        message=message,
    )


def _policy_failure(validation: ValidationResult) -> ExecutionResult:
    return ExecutionResult(
        ExecutionStatus.POLICY_FAILURE,
        validation,
        None,
        "",
        "",
        None,
        0.0,
        message=validation.message or "Code was not approved by policy.",
    )


def _attach_validation(result: ExecutionResult, validation: ValidationResult) -> ExecutionResult:
    return ExecutionResult(
        result.status,
        validation,
        result.returncode,
        result.stdout,
        result.stderr,
        result.answer,
        result.duration_seconds,
        result.timed_out,
        result.output_truncated,
        result.message,
    )


def execute_validated(
    validation: ValidationResult,
    limits: ExecutionLimits | None = None,
) -> ExecutionResult:
    """Execute only a successful strict AST validation result in a fresh process."""

    if validation.valid and validation.code is not None:
        validation = validate_code(validation.code)
    if not validation.valid or validation.code is None:
        return _policy_failure(validation)
    result = _execute_approved_code(validation.code, limits or ExecutionLimits())
    return _attach_validation(result, validation)


def execute_compatible_validated(
    validation: ValidationResult,
    limits: ExecutionLimits | None = None,
) -> ExecutionResult:
    """Execute exact compatible-extracted source after rechecking the safety allowlist."""

    if validation.valid and validation.code is not None:
        validation = validate_code_compatible(validation.code)
    if not validation.valid or validation.code is None:
        return _policy_failure(validation)
    result = _execute_approved_code(
        validation.code,
        limits or ExecutionLimits(),
        enforce_answer_contract=False,
    )
    return _attach_validation(result, validation)


def execute_response(response: str, limits: ExecutionLimits | None = None) -> ExecutionResult:
    """Validate a raw fenced response and execute it only if strict policy approves it."""

    return execute_validated(validate_response(response), limits)
