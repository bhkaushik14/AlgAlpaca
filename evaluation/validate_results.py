"""Validate the compact public confirmatory result package without inference."""

from __future__ import annotations

import csv
from collections import Counter
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
HISTORICAL_COLUMNS = {
    "case_id",
    "category",
    "base_correct",
    "adapter_correct",
    "base_failure_category",
    "adapter_failure_category",
}
V2_REQUIRED_COLUMNS = {
    "case_id",
    "category",
    "raw_response",
    "extracted_code",
    "extraction_status",
    "syntax_status",
    "policy_status",
    "execution_status",
    "stdout",
    "automated_correct",
    "failure_reason",
    "manual_reviewed",
    "manual_correct",
    "manual_classification",
    "manual_note",
}
V2_RESULTS_SHA256 = "d67014f8d12747c640dc33d7b8b948206e7928269d8765d3a18d5f843a990e21"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate() -> dict[str, int]:
    cases = [
        json.loads(line)
        for line in (ROOT / "confirmatory_cases.jsonl").read_text().splitlines()
        if line
    ]
    with (ROOT / "case_results.csv").open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        if set(reader.fieldnames or ()) != HISTORICAL_COLUMNS:
            raise ValueError("unexpected case-results columns")
        rows = list(reader)
    v2_path = ROOT / "v2_case_results.csv"
    if _sha256(v2_path) != V2_RESULTS_SHA256:
        raise ValueError("v2 per-case artifact identity changed")
    with v2_path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        if not V2_REQUIRED_COLUMNS.issubset(reader.fieldnames or ()):
            raise ValueError("unexpected v2 case-results columns")
        v2_rows = list(reader)
    if len(cases) != 100 or len(rows) != 100 or len(v2_rows) != 100:
        raise ValueError("fixture and result files must contain 100 cases")
    case_ids = [case["id"] for case in cases]
    case_categories = [case["category"] for case in cases]
    if (
        [row["case_id"] for row in rows] != case_ids
        or [row["case_id"] for row in v2_rows] != case_ids
        or [row["category"] for row in rows] != case_categories
        or [row["category"] for row in v2_rows] != case_categories
        or len(set(case_ids)) != 100
    ):
        raise ValueError("case IDs, categories, or deterministic order differ from the fixture")
    base = sum(row["base_correct"] == "true" for row in rows)
    adapter = sum(row["adapter_correct"] == "true" for row in rows)
    paired = {
        "adapter_only_correct": sum(
            r["base_correct"] == "false" and r["adapter_correct"] == "true" for r in rows
        ),
        "base_only_correct": sum(
            r["base_correct"] == "true" and r["adapter_correct"] == "false" for r in rows
        ),
        "both_correct": sum(
            r["base_correct"] == "true" and r["adapter_correct"] == "true" for r in rows
        ),
        "both_incorrect": sum(
            r["base_correct"] == "false" and r["adapter_correct"] == "false" for r in rows
        ),
    }
    if (base, adapter, paired) != (
        17,
        39,
        {
            "adapter_only_correct": 27,
            "base_only_correct": 5,
            "both_correct": 12,
            "both_incorrect": 56,
        },
    ):
        raise ValueError("reported scores or paired counts changed")
    v2 = sum(row["automated_correct"] == "True" for row in v2_rows)
    manual = sum(row["manual_correct"] == "True" for row in v2_rows)
    executable = sum(row["execution_status"] == "ok" for row in v2_rows)
    equivalence = sum(row["manual_classification"] == "scorer_false_negative" for row in v2_rows)
    stage_failures = {
        "execution": sum(row["execution_status"] not in {"ok", "not_reached"} for row in v2_rows),
        "extraction": sum(row["extraction_status"].startswith("failed:") for row in v2_rows),
        "mathematical_score": sum(row["failure_reason"].startswith("scoring_error:") for row in v2_rows),
        "policy": sum(row["policy_status"] == "failed" for row in v2_rows),
        "stdout": sum(row["failure_reason"].startswith("stdout_error:") for row in v2_rows),
        "syntax": sum(row["syntax_status"] == "failed" for row in v2_rows),
    }
    remaining = {
        "execution_failure": sum(row["manual_classification"] == "execution_failure" for row in v2_rows),
        "mathematically_wrong_answer": sum(row["manual_classification"] == "mathematically_wrong_answer" for row in v2_rows),
        "policy_failure": sum(row["manual_classification"] == "policy_failure" for row in v2_rows),
    }
    original_flags = [row["adapter_correct"] == "true" for row in rows]
    v2_flags = [row["automated_correct"] == "True" for row in v2_rows]
    paired_v2 = {
        "both_correct": sum(old and new for old, new in zip(original_flags, v2_flags)),
        "both_incorrect": sum(not old and not new for old, new in zip(original_flags, v2_flags)),
        "original_only": sum(old and not new for old, new in zip(original_flags, v2_flags)),
        "v2_only": sum(not old and new for old, new in zip(original_flags, v2_flags)),
    }
    category_counts = {}
    for category in dict.fromkeys(case_categories):
        positions = [index for index, value in enumerate(case_categories) if value == category]
        category_counts[category] = {
            "adapter_correct": sum(original_flags[index] for index in positions),
            "base_correct": sum(rows[index]["base_correct"] == "true" for index in positions),
            "v2_automated_correct": sum(v2_flags[index] for index in positions),
            "v2_manual_correct": sum(
                v2_rows[index]["manual_correct"] == "True" for index in positions
            ),
            "cases": len(positions),
        }
    v2_failure_distribution = dict(Counter(row["failure_reason"] for row in v2_rows))
    if (v2, manual, executable, equivalence) != (59, 71, 85, 12):
        raise ValueError("v2 correctness, executable, or equivalence totals changed")
    if not all(row["manual_reviewed"] == "True" for row in v2_rows):
        raise ValueError("v2 manual review is incomplete")
    if stage_failures != {
        "execution": 8,
        "extraction": 0,
        "mathematical_score": 26,
        "policy": 7,
        "stdout": 0,
        "syntax": 0,
    }:
        raise ValueError("v2 failure-stage totals changed")
    if remaining != {
        "execution_failure": 8,
        "mathematically_wrong_answer": 14,
        "policy_failure": 7,
    }:
        raise ValueError("v2 manual failure classifications changed")
    if paired_v2 != {
        "both_correct": 28,
        "both_incorrect": 30,
        "original_only": 11,
        "v2_only": 31,
    }:
        raise ValueError("paired original-v2 counts changed")
    summary = json.loads((ROOT / "summary.json").read_text())
    if (
        summary["conditions"]["base"]["primary_correctness"]["numerator"] != base
        or summary["conditions"]["adapter"]["primary_correctness"]["numerator"] != adapter
        or summary["conditions"]["v2"]["primary_correctness"]["numerator"] != v2
        or summary["conditions"]["v2"]["manual_correctness"]["numerator"] != manual
        or summary["conditions"]["v2"]["executable"]["numerator"] != executable
        or summary["conditions"]["v2"]["failure_distribution"] != v2_failure_distribution
        or summary["paired_outcomes"] != paired
        or summary["paired_original_v2_automated"] != paired_v2
        or summary["conditions"]["v2"]["stage_failures"] != stage_failures
        or summary["conditions"]["v2"]["remaining_manual_failures"] != remaining
        or summary["per_category"] != category_counts
        or summary["provenance"]["v2"]["per_case_results_sha256"] != V2_RESULTS_SHA256
        or summary["provenance"]["sha256"]["evaluation/v2_case_results.csv"]
        != V2_RESULTS_SHA256
    ):
        raise ValueError("summary does not match case results")
    text = (ROOT / "case_results.csv").read_text().lower()
    if "/home/" in text or "raw_response" in text or "generated_program" in text:
        raise ValueError("compact results contain prohibited data")
    return {
        "cases": len(rows),
        "base_correct": base,
        "adapter_correct": adapter,
        "v2_automated_correct": v2,
        "v2_manual_correct": manual,
        "v2_executable": executable,
        "v2_scorer_false_negatives": equivalence,
        **paired,
        "original_v2_both_correct": paired_v2["both_correct"],
        "original_v2_both_incorrect": paired_v2["both_incorrect"],
        "original_v2_original_only": paired_v2["original_only"],
        "original_v2_v2_only": paired_v2["v2_only"],
    }


if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))
