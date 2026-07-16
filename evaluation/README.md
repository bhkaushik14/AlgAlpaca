# Evaluation

## Fixture

`confirmatory_cases.jsonl` contains the exact 100-case fixture used for the reported comparison. It covers linear, quadratic, rational, absolute-value, exponential, logarithmic, system, inequality, function-evaluation, and expression-simplification tasks. Each case records the problem, category, expected mathematical form, and scoring information.

## Method

The comparison used identical frozen prompting for the base and adapter conditions. Each condition received one deterministic generation attempt per case with no repair. The pipeline extracted Python, checked syntax and execution policy, ran accepted programs in the restricted subprocess, and compared parsed output with the expected mathematical result.

Generated source was not compared with reference source. A correct result required executable output with the expected mathematical meaning. The local execution sandbox reduces risk but is not hardened for public multi-tenant use.

## Results

| Condition | Correct |
|---|---:|
| Base model | 17/100 |
| Fine-tuned adapter | 39/100 |

Paired outcomes were adapter-only 27, base-only 5, both correct 12, and both incorrect 56. Category and failure-type counts are in `summary.json`; the six-field, one-row-per-case comparison is in `case_results.csv`.

The adapter improved under this evaluation but remained unreliable. Frequent failures included incorrect mathematics, missing or unusable output, policy rejection, and runtime or syntax errors. Domains and inequalities remained difficult. The evaluation is prompt-sensitive and does not support claims about external benchmarks, statistical significance, or general mathematical performance.

## Manual review

All 200 condition-case records were manually reviewed. Review found no automated/manual correctness disagreements, subjective credit changes, invalid fixture cases, or denominator changes. Review checked functional correctness and failure classification; it did not award credit based on resemblance to a reference program.

## Files and validation

- `confirmatory_cases.jsonl`: exact frozen questions and scoring specifications.
- `case_results.csv`: compact correctness and failure category for both conditions.
- `summary.json`: total, paired, category, and failure-type counts.
- `validate_confirmatory.py`: validates fixture structure and frozen integrity.
- `policy_conformance.py`: model-independent execution-policy conformance checks.
- `validate_results.py`: validates the compact result package and reported counts.

No model generation was performed to create this package. Compact artifacts were deterministically derived from these frozen files in the separate archival repository:

| Archival relative path | SHA-256 |
|---|---|
| `evaluation/confirmatory_cases.jsonl` | `6a1a6bea174f298192a3b103d979e630d04405d562434eac1b7603c3a57d2a24` |
| `evaluation/results/confirmatory/manual_review.json` | `03bc1ce3e4b201a94a22098214fc6d397d2e6543b4f2befa25d75a31365fb2af` |
| `evaluation/results/confirmatory/summary.json` | `a409b6b5cd929dda877d91cb873f800cc5e337ceac26a6e034293844c1b31b0b` |
| `evaluation/results/confirmatory/base_results.jsonl` | `e1011010a313b3e4283f25ca218e2bdf318c67ac134aee4d65cafa811a555753` |
| `evaluation/results/confirmatory/adapter_results.jsonl` | `d92c3cb704abacc98e6c6fd5667c66dbcc9c41f914912f0be63859145708afca` |
