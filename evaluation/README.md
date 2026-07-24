# Evaluation

## Fixture

`confirmatory_cases.jsonl` contains the exact 100-case fixture used for all three automated scores. Its SHA-256 is `6a1a6bea174f298192a3b103d979e630d04405d562434eac1b7603c3a57d2a24`. It covers linear, quadratic, rational, absolute-value, exponential, logarithmic, system, inequality, function-evaluation, and expression-simplification tasks.

## Method

The base model, original adapter, and v2 adapter used prompt version `confirmatory-algebra-to-code-v2` with the same frozen Code Llama base revision `22cb240e0292b0b5ab4c17ccd97aa3a2f799cbed`. Each condition received one deterministic greedy generation per case with a 768-new-token limit, seed 42, no sampling, no repair, and no retries.

The pipeline extracted Python, checked syntax and execution policy, ran accepted programs in the restricted subprocess, and compared parsed output with the expected mathematical result. The retained corrected extractor already accepted a complete raw response when the entire nonempty response parsed as one Python module, so v2 required no public evaluator or extractor change.

Generated source was not compared with reference source. A correct result required executable output with the expected mathematical meaning. The local execution sandbox reduces risk but is not hardened for public multi-tenant use.

## Results

| Condition | Automated correct | Separate v2 manual review | Executable |
|---|---:|---:|---:|
| Base model | 17/100 | — | 38/100 |
| Original adapter | 39/100 | — | 61/100 |
| V2 adapter | **59/100** | **71/100** | **85/100** |

The 17/100, 39/100, and 59/100 results are directly comparable outputs from the same frozen automated protocol. Manual review found 12 additional v2 outputs that were mathematically equivalent but rejected by the scorer; 71/100 is the reviewed mathematical total, not v2 automated accuracy.

Paired original-v2 automated outcomes were both correct 28, original only 11, v2 only 31, and both incorrect 30. The retained base-original paired counts remain adapter-only 27, base-only 5, both correct 12, and both incorrect 56.

### V2 category results

| Category | Automated | Manual |
|---|---:|---:|
| Absolute value | 10/10 | 10/10 |
| Exponents and radicals | 6/10 | 7/10 |
| Inequalities | 6/10 | 7/10 |
| Linear equations | 7/10 | 9/10 |
| Polynomial roots or factorization | 9/10 | 9/10 |
| Proportions and word problems | 0/10 | 0/10 |
| Quadratic equations | 8/10 | 9/10 |
| Rational equations | 8/10 | 8/10 |
| Simplification or evaluation | 5/10 | 6/10 |
| Systems of equations | 0/10 | 6/10 |

### V2 failure stages

Automated scoring recorded 0 extraction failures, 0 syntax failures, 7 policy failures, 8 execution failures, and 26 mathematical-score failures. V2 produced executable output in 85 cases.

Manual review classified 12 scorer false negatives. The remaining failures were 14 mathematically wrong answers, 8 execution failures, and 7 policy failures.

The result applies only to this fixture, prompt, and scoring method. It does not support claims about external benchmarks, statistical significance, or general mathematical performance.

## Manual review

All 200 historical base/original condition-case records remain unchanged. Their review found no automated/manual correctness disagreements, subjective credit changes, invalid fixture cases, or denominator changes.

All 100 v2 records were also inspected. Twelve were clear scorer false negatives involving decimal or float equivalents (`confirm-linear-03`, `confirm-linear-04`, `confirm-quadratic-09`, `confirm-system-10`, `confirm-inequality-02`), ordered system tuples (`confirm-system-01`, `confirm-system-02`, `confirm-system-04`, `confirm-system-05`, `confirm-system-09`), or equivalent exact collection/expression forms (`confirm-simplify-05`, `confirm-exponent-08`).

The systems automated score was 0/10, while manual review accepted six mathematically equivalent ordered outputs. This is a scorer representation issue, not evidence that every system program was valid: the other four system cases remained wrong or failed during execution.

## Files and validation

- `confirmatory_cases.jsonl`: exact frozen questions and scoring specifications.
- `case_results.csv`: retained compact base/original correctness and failure categories.
- `v2_case_results.csv`: complete v2 per-case responses, pipeline stages, automated scores, and manual determinations.
- `summary.json`: three-model totals, paired outcomes, categories, failure counts, and provenance.
- `comparison.md`: concise base/original/v2 comparison.
- `validate_confirmatory.py`: validates fixture structure and frozen integrity.
- `policy_conformance.py`: model-independent execution-policy conformance checks.
- `validate_results.py`: validates historical and v2 rows, totals, paired counts, and failure accounting.

## V2 checkpoint identity

The evaluated v2 checkpoint completed at optimizer step 825. Its adapter weight SHA-256 is `a56735e268a5343a02966d3ad8513c2b4a6232b2ed97e9dcdfaa70404293215d`.
Its adapter config SHA-256 is `67625139ecb7f71fee57be953ba8070a3f2f0981691038781747aa05b602e797`.
It uses the same frozen Code Llama base revision listed above.

The public `v2_case_results.csv` is copied from the completed evaluation artifact with SHA-256 `d67014f8d12747c640dc33d7b8b948206e7928269d8765d3a18d5f843a990e21`. It already contains every raw response, so the duplicate raw-output JSONL is intentionally omitted.

The retained historical compact artifacts were deterministically derived without new model generation from these frozen files in the separate archival repository:

| Archival relative path | SHA-256 |
|---|---|
| `evaluation/confirmatory_cases.jsonl` | `6a1a6bea174f298192a3b103d979e630d04405d562434eac1b7603c3a57d2a24` |
| `evaluation/results/confirmatory/manual_review.json` | `03bc1ce3e4b201a94a22098214fc6d397d2e6543b4f2befa25d75a31365fb2af` |
| `evaluation/results/confirmatory/summary.json` | `a409b6b5cd929dda877d91cb873f800cc5e337ceac26a6e034293844c1b31b0b` |
| `evaluation/results/confirmatory/base_results.jsonl` | `e1011010a313b3e4283f25ca218e2bdf318c67ac134aee4d65cafa811a555753` |
| `evaluation/results/confirmatory/adapter_results.jsonl` | `d92c3cb704abacc98e6c6fd5667c66dbcc9c41f914912f0be63859145708afca` |
