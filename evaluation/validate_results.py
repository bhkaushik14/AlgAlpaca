"""Validate the compact public confirmatory result package without inference."""

from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REQUIRED_COLUMNS = {
    "case_id",
    "category",
    "base_correct",
    "adapter_correct",
    "base_failure_category",
    "adapter_failure_category",
}


def validate() -> dict[str, int]:
    cases = [
        json.loads(line)
        for line in (ROOT / "confirmatory_cases.jsonl").read_text().splitlines()
        if line
    ]
    with (ROOT / "case_results.csv").open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        if set(reader.fieldnames or ()) != REQUIRED_COLUMNS:
            raise ValueError("unexpected case-results columns")
        rows = list(reader)
    if len(cases) != 100 or len(rows) != 100:
        raise ValueError("fixture and compact results must contain 100 cases")
    case_ids = [case["id"] for case in cases]
    if [row["case_id"] for row in rows] != case_ids or len(set(case_ids)) != 100:
        raise ValueError("case IDs or deterministic order differ from the fixture")
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
    summary = json.loads((ROOT / "summary.json").read_text())
    if (
        summary["conditions"]["base"]["primary_correctness"]["numerator"] != base
        or summary["conditions"]["adapter"]["primary_correctness"]["numerator"] != adapter
        or summary["paired_outcomes"] != paired
    ):
        raise ValueError("summary does not match case results")
    text = (ROOT / "case_results.csv").read_text().lower()
    if "/home/" in text or "raw_response" in text or "generated_program" in text:
        raise ValueError("compact results contain prohibited data")
    return {"cases": len(rows), "base_correct": base, "adapter_correct": adapter, **paired}


if __name__ == "__main__":
    print(json.dumps(validate(), sort_keys=True))
