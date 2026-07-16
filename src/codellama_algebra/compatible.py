"""Post-hoc compatible extraction and observable-output parsing.

This module is deliberately separate from the frozen strict evaluator. It removes only an
accepted response wrapper plus outer whitespace/line-ending differences. It never repairs,
combines, completes, or otherwise rewrites generated source.
"""

from __future__ import annotations

import ast
import hashlib
import re
from dataclasses import dataclass

_MARKDOWN_FENCE = re.compile(
    r"```(?P<label>[^\r\n`]*)\r?\n(?P<code>.*?)```",
    re.DOTALL,
)
_LLM_CODE = re.compile(r"<llm-code>(?P<code>.*?)</llm-code>", re.IGNORECASE | re.DOTALL)
_BOXED = re.compile(r"\\boxed\{(?P<answer>[^{}\r\n]+)\}")
_ANSWER_PHRASE = re.compile(
    r"(?im)\b(?:the\s+)?answer\s*(?:is|:)\s*(?P<answer>[^\r\n]+?)\s*$"
)
_SUPPORTED_LABELS = {"python": "explicit_python_fence", "py": "python_alias_fence", "python3": "python_alias_fence"}


@dataclass(frozen=True)
class CompatibleExtraction:
    """One auditable extraction result with exact source locations and hashes."""

    valid: bool
    code: str | None
    wrapper_type: str | None
    error_code: str | None
    message: str | None
    raw_response_sha256: str
    code_sha256: str | None = None
    source_start: int | None = None
    source_end: int | None = None
    wrapper_start: int | None = None
    wrapper_end: int | None = None
    candidate_count: int = 0
    transformations: tuple[str, ...] = ()
    semantic_edits: bool = False


@dataclass(frozen=True)
class FormatClassification:
    """Multi-label response-shape classification used by the frozen-output census."""

    primary_category: str
    labels: tuple[str, ...]
    markdown_block_count: int
    markdown_labels: tuple[str, ...]
    legacy_llm_code_block_count: int
    compatible_extraction_status: str


@dataclass(frozen=True)
class ObservableResult:
    """An answer candidate selected only by the documented stdout hierarchy."""

    status: str
    answer: str | None
    mode: str | None
    nonempty_line_count: int
    answer_line_count: int
    answer_line_index: int | None = None
    diagnostic_lines: tuple[str, ...] = ()
    message: str | None = None


@dataclass(frozen=True)
class DirectAnswerResult:
    """A separately reported non-code answer candidate from a raw response."""

    valid: bool
    answer: str | None
    mode: str | None
    source_start: int | None
    source_end: int | None
    error_code: str | None = None
    message: str | None = None


@dataclass(frozen=True)
class _Candidate:
    wrapper_type: str
    code_start: int
    code_end: int
    wrapper_start: int
    wrapper_end: int


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _parseable_python(text: str) -> bool:
    if not text.strip():
        return False
    try:
        ast.parse(text.strip(), mode="exec")
    except SyntaxError:
        return False
    return True


def _trimmed_span(response: str, start: int, end: int) -> tuple[int, int, str, tuple[str, ...]]:
    source = response[start:end]
    leading = len(source) - len(source.lstrip())
    trailing = len(source) - len(source.rstrip())
    source_start = start + leading
    source_end = end - trailing if trailing else end
    exact = response[source_start:source_end]
    transformations: list[str] = []
    if leading or trailing:
        transformations.append("trimmed_outer_whitespace")
    normalized = exact.replace("\r\n", "\n").replace("\r", "\n")
    if normalized != exact:
        transformations.append("normalized_line_endings")
    return source_start, source_end, normalized, tuple(transformations)


def extract_compatible_code(response: str) -> CompatibleExtraction:
    """Extract one unambiguous accepted source form without changing program semantics."""

    raw_hash = _sha256_text(response)
    markdown = list(_MARKDOWN_FENCE.finditer(response))
    legacy = list(_LLM_CODE.finditer(response))
    candidates: list[_Candidate] = []

    for match in markdown:
        label = match.group("label").strip().casefold()
        wrapper_type = _SUPPORTED_LABELS.get(label)
        if wrapper_type is None and label == "" and _parseable_python(match.group("code")):
            wrapper_type = "unlabeled_markdown_fence"
        if wrapper_type is not None:
            candidates.append(
                _Candidate(
                    wrapper_type,
                    match.start("code"),
                    match.end("code"),
                    match.start(),
                    match.end(),
                )
            )
    for match in legacy:
        candidates.append(
            _Candidate(
                "legacy_llm_code",
                match.start("code"),
                match.end("code"),
                match.start(),
                match.end(),
            )
        )

    if len(candidates) > 1:
        return CompatibleExtraction(
            False,
            None,
            None,
            "ambiguous_code_blocks",
            "More than one plausible source block is present.",
            raw_hash,
            candidate_count=len(candidates),
        )
    if len(candidates) == 1:
        candidate = candidates[0]
        start, end, code, transforms = _trimmed_span(
            response, candidate.code_start, candidate.code_end
        )
        transforms = (f"removed_{candidate.wrapper_type}",) + transforms
        return CompatibleExtraction(
            True,
            code,
            candidate.wrapper_type,
            None,
            None,
            raw_hash,
            _sha256_text(code),
            start,
            end,
            candidate.wrapper_start,
            candidate.wrapper_end,
            1,
            transforms,
        )

    has_wrapper_markup = bool(
        "```" in response
        or re.search(r"</?llm-code(?:-output)?>", response, re.IGNORECASE)
        or re.search(r"</?llm-code", response, re.IGNORECASE)
    )
    if not has_wrapper_markup and _parseable_python(response):
        start, end, code, transforms = _trimmed_span(response, 0, len(response))
        return CompatibleExtraction(
            True,
            code,
            "raw_python",
            None,
            None,
            raw_hash,
            _sha256_text(code),
            start,
            end,
            0,
            len(response),
            1,
            transforms,
        )

    if not response.strip():
        error_code = "no_code"
        message = "Response is empty."
    elif markdown and any(match.group("label").strip() for match in markdown):
        error_code = "unsupported_wrapper"
        message = "No supported Python fence label is present."
    elif has_wrapper_markup:
        error_code = "malformed_or_unsupported_wrapper"
        message = "Wrapper markup is malformed or does not identify executable source."
    else:
        error_code = "raw_python_invalid"
        message = "The complete raw response is not valid Python source."
    return CompatibleExtraction(False, None, None, error_code, message, raw_hash)


def _outside_wrapper_has_text(response: str, extraction: CompatibleExtraction) -> bool:
    if extraction.wrapper_start is None or extraction.wrapper_end is None:
        return False
    return bool(
        response[: extraction.wrapper_start].strip() or response[extraction.wrapper_end :].strip()
    )


def classify_response_format(response: str) -> FormatClassification:
    """Return a deterministic primary category plus nonexclusive census labels."""

    extraction = extract_compatible_code(response)
    markdown = list(_MARKDOWN_FENCE.finditer(response))
    legacy = list(_LLM_CODE.finditer(response))
    markdown_labels = tuple(match.group("label").strip() for match in markdown)
    labels: set[str] = set()
    if not response.strip():
        labels.add("empty_response")
    for label_text in markdown_labels:
        label = label_text.casefold()
        if label == "python":
            labels.add("explicit_python_fence")
        elif label in {"py", "python3"}:
            labels.add("python_alias_fence")
        elif label == "":
            labels.add("unlabeled_markdown_fence")
        else:
            labels.add("other_labeled_fence")
    if legacy:
        labels.add("legacy_llm_code")
    if len(markdown) + len(legacy) > 1:
        labels.add("multiple_code_blocks")
    if response.count("```") % 2 or (
        re.search(r"<llm-code>", response, re.IGNORECASE) and not legacy
    ):
        labels.update(("malformed_wrapper", "truncated_response"))
    elif re.search(r"</?llm-code(?:-output)?>", response, re.IGNORECASE) and not legacy:
        labels.add("malformed_wrapper")

    tree: ast.Module | None = None
    no_complete_wrapper = not markdown and not legacy and "```" not in response
    if no_complete_wrapper and _parseable_python(response):
        labels.add("raw_python")
        tree = ast.parse(response.strip(), mode="exec")
        if len(tree.body) == 1 and isinstance(tree.body[0], ast.Expr):
            labels.add("plain_expression")
    direct = extract_direct_answer(response)
    if direct.valid:
        labels.add("direct_answer")
    if extraction.valid and extraction.wrapper_type != "raw_python" and _outside_wrapper_has_text(
        response, extraction
    ):
        labels.add("prose_with_inline_code")
    elif re.search(r"(?<!`)`[^`\r\n]+`(?!`)", response):
        labels.add("prose_with_inline_code")
    if not extraction.valid:
        labels.add("no_compatible_code")

    priority = (
        "empty_response",
        "multiple_code_blocks",
        "explicit_python_fence",
        "python_alias_fence",
        "unlabeled_markdown_fence",
        "legacy_llm_code",
        "other_labeled_fence",
        "raw_python",
        "direct_answer",
        "truncated_response",
        "malformed_wrapper",
        "prose_with_inline_code",
        "plain_expression",
        "no_compatible_code",
    )
    primary = next((name for name in priority if name in labels), "no_compatible_code")
    return FormatClassification(
        primary,
        tuple(sorted(labels)),
        len(markdown),
        markdown_labels,
        len(legacy),
        "accepted" if extraction.valid else extraction.error_code or "rejected",
    )


def parse_observable_stdout(stdout: str) -> ObservableResult:
    """Select an observable candidate without using last-line or best-looking heuristics."""

    lines = [(index, line.strip()) for index, line in enumerate(stdout.splitlines()) if line.strip()]
    answer_lines = [(index, line) for index, line in lines if line.startswith("ANSWER:")]
    if len(answer_lines) > 1:
        return ObservableResult(
            "ambiguous_stdout",
            None,
            None,
            len(lines),
            len(answer_lines),
            message="Multiple nonempty ANSWER: lines are present.",
        )
    if len(answer_lines) == 1:
        index, line = answer_lines[0]
        answer = line[len("ANSWER:") :].strip()
        if not answer:
            return ObservableResult(
                "malformed_answer",
                None,
                None,
                len(lines),
                1,
                index,
                message="The unique ANSWER: line is empty.",
            )
        diagnostics = tuple(line for line_index, line in lines if line_index != index)
        return ObservableResult(
            "observable",
            answer,
            "unique_answer_line",
            len(lines),
            1,
            index,
            diagnostics,
        )
    if not lines:
        return ObservableResult(
            "no_output",
            None,
            None,
            0,
            0,
            message="The program produced no nonempty stdout line.",
        )
    if len(lines) == 1:
        index, line = lines[0]
        return ObservableResult(
            "observable",
            line,
            "unique_nonempty_line",
            1,
            0,
            index,
        )
    return ObservableResult(
        "ambiguous_stdout",
        None,
        None,
        len(lines),
        0,
        message="Multiple nonempty lines are present without a unique ANSWER: line.",
    )


def extract_direct_answer(response: str) -> DirectAnswerResult:
    """Extract only an unambiguous non-code answer candidate for a separate diagnostic."""

    if _MARKDOWN_FENCE.search(response) or _LLM_CODE.search(response):
        return DirectAnswerResult(
            False, None, None, None, None, "contains_code", "Response contains a source block."
        )
    boxed = list(_BOXED.finditer(response))
    if len(boxed) > 1:
        return DirectAnswerResult(
            False,
            None,
            None,
            None,
            None,
            "ambiguous_direct_answer",
            "Multiple boxed answers are present.",
        )
    if len(boxed) == 1:
        match = boxed[0]
        return DirectAnswerResult(
            True,
            match.group("answer").strip(),
            "boxed_answer",
            match.start("answer"),
            match.end("answer"),
        )
    phrases = list(_ANSWER_PHRASE.finditer(response))
    if len(phrases) > 1:
        return DirectAnswerResult(
            False,
            None,
            None,
            None,
            None,
            "ambiguous_direct_answer",
            "Multiple explicit answer phrases are present.",
        )
    if len(phrases) == 1:
        match = phrases[0]
        answer = match.group("answer").strip().rstrip(".")
        start = match.start("answer")
        return DirectAnswerResult(True, answer, "answer_phrase", start, start + len(answer))

    stripped = response.strip()
    if (
        stripped
        and "\n" not in stripped
        and "\r" not in stripped
        and "```" not in stripped
        and "<llm-code" not in stripped.casefold()
    ):
        start = response.index(stripped)
        return DirectAnswerResult(
            True, stripped, "whole_single_line", start, start + len(stripped)
        )
    return DirectAnswerResult(
        False,
        None,
        None,
        None,
        None,
        "no_direct_answer",
        "No unambiguous direct-answer form is present.",
    )
