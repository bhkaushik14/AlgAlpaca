"""Thin CLI over the shared model, generation, validation, and execution layers."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from .generation import GenerationConfig, generate_problem
from .model import ADAPTER_REPO_ID, BASE_MODEL_ID, ModelLoadConfig, QuantizationConfig, load_model
from .sandbox import execute_validated


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate validated Python/SymPy for one algebra problem."
    )
    parser.add_argument(
        "--metadata", action="store_true", help="Show configured source metadata only."
    )
    parser.add_argument("--problem", help="Algebra problem to translate into Python/SymPy.")
    parser.add_argument(
        "--adapter", default=ADAPTER_REPO_ID, help="Explicit adapter path or HF ID."
    )
    parser.add_argument("--base-model", default=BASE_MODEL_ID)
    parser.add_argument("--max-new-tokens", type=int, default=768)
    parser.add_argument("--no-four-bit", action="store_true")
    parser.add_argument("--local-files-only", action="store_true")
    parser.add_argument(
        "--execute", action="store_true", help="Run approved code in the local evaluator."
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI without duplicating inference or policy behavior."""

    args = _parser().parse_args(argv)
    configured = {
        "base_model_id": args.base_model,
        "adapter_id_or_path": args.adapter,
        "quantized_4bit": not args.no_four_bit,
        "deterministic_generation": True,
        "max_new_tokens": args.max_new_tokens,
        "local_files_only": args.local_files_only,
        "model_loaded": False,
    }
    if args.metadata:
        print(json.dumps(configured, indent=2))
        return 0
    if not args.problem:
        _parser().error("--problem is required unless --metadata is used")

    loaded = load_model(
        ModelLoadConfig(
            adapter_id_or_path=args.adapter,
            base_model_id=args.base_model,
            quantization=QuantizationConfig(enabled=not args.no_four_bit),
            local_files_only=args.local_files_only,
        )
    )
    generated = generate_problem(
        loaded,
        args.problem,
        GenerationConfig(max_new_tokens=args.max_new_tokens),
    )
    report = {
        "model_metadata": asdict(loaded.metadata),
        "raw_output": generated.raw_response,
        "all_raw_attempts": [attempt.raw_response for attempt in generated.attempts],
        "extracted_code": generated.extracted_code,
        "validation": asdict(generated.validation),
        "repair_used": generated.repair_used,
    }
    if args.execute:
        execution = execute_validated(generated.validation)
        report["execution"] = asdict(execution)
        report["execution"]["status"] = execution.status.value
        report["extracted_answer"] = execution.answer
    print(json.dumps(report, indent=2))
    return 0 if generated.validation.valid else 2


if __name__ == "__main__":
    raise SystemExit(main())
