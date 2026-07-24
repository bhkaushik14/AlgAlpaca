# AlgAlpaca v2 frozen 100-case comparison

- Frozen fixture: `confirmatory_cases.jsonl`
- Fixture SHA-256: `6a1a6bea174f298192a3b103d979e630d04405d562434eac1b7603c3a57d2a24`
- Base automated correctness: **17/100**
- Base executable programs: **38/100**
- Original adapter automated correctness: **39/100**
- Original adapter executable programs: **61/100**
- V2 automated correctness: **59/100**
- V2 manually reviewed mathematical total: **71/100**
- V2 executable programs: **85/100**
- Raw-Python compatibility: the retained corrected extractor already accepted raw Python; no extraction change was made.

The primary apples-to-apples progression is **17% → 39% → 59%**. The 71/100 figure is a separate manual mathematical review.

## Category results

| Category | Automated | Manual | Cases |
|---|---:|---:|---:|
| absolute_value_equations | 10 | 10 | 10 |
| exponents_and_radicals | 6 | 7 | 10 |
| inequalities | 6 | 7 | 10 |
| linear_equations | 7 | 9 | 10 |
| polynomial_roots_or_factorization | 9 | 9 | 10 |
| proportions_and_word_problems | 0 | 0 | 10 |
| quadratic_equations | 8 | 9 | 10 |
| rational_equations | 8 | 8 | 10 |
| simplification_or_evaluation | 5 | 6 | 10 |
| systems_of_equations | 0 | 6 | 10 |

## Paired original versus v2 automated outcomes

- Both correct: 28
- Original only: 11
- V2 only: 31
- Both incorrect: 30

## V2 failures

- Extraction failures: 0
- Syntax failures: 0
- Policy failures: 7
- Execution failures: 8
- Automated mathematical-score failures: 26

## Clear scorer-equivalence cases

- confirm-linear-03: expected `['23/5']`, actual `[4.60000000000000]` — The printed decimal is the decimal representation of 23/5.
- confirm-linear-04: expected `['-18/7']`, actual `[-2.57142857142857]` — The printed decimal is the displayed floating-point approximation of -18/7.
- confirm-quadratic-09: expected `['4/3', '2']`, actual `{1.33333333333333, 2.0}` — The two printed floats numerically represent the expected roots 4/3 and 2.
- confirm-system-01: expected `{'x': '55/13', 'y': '41/13'}`, actual `{(55/13, 41/13)}` — The ordered tuple (55/13, 41/13) matches variables (x, y).
- confirm-system-02: expected `{'x': '1', 'y': '5'}`, actual `{(1, 5)}` — The ordered tuple (1, 5) matches variables (x, y).
- confirm-system-04: expected `{'x': '2', 'y': '-1', 'z': '3'}`, actual `{(2, -1, 3)}` — The ordered tuple (2, -1, 3) matches variables (x, y, z).
- confirm-system-05: expected `{'x': '-2', 'y': '4', 'z': '1'}`, actual `{(-2, 4, 1)}` — The ordered tuple (-2, 4, 1) matches variables (x, y, z).
- confirm-system-09: expected `{'p': '71/17', 'q': '-25/17'}`, actual `{(71/17, -25/17)}` — The ordered tuple (71/17, -25/17) matches variables (p, q).
- confirm-system-10: expected `{'x': '1/2', 'y': '2/3', 'z': '-1'}`, actual `{(0.5, 0.666666666666667, -1.0)}` — The ordered float tuple numerically represents (1/2, 2/3, -1).
- confirm-inequality-02: expected `Interval(6, oo)`, actual `Interval(6.00000000000000, oo)` — Interval(6.00000000000000, oo) is the expected closed interval from 6.
- confirm-simplify-05: expected `6 + 2*sqrt(5)`, actual `{(1 + sqrt(5))**2}` — The singleton contains (1 + sqrt(5))**2, exactly equal to 6 + 2*sqrt(5).
- confirm-exponent-08: expected `3.4594316186372973`, actual `{log(11)/log(2)}` — The exact singleton log(11)/log(2) equals the requested decimal approximation.

## Remaining manually confirmed failure modes

- execution_failure: 8
- mathematically_wrong_answer: 14
- policy_failure: 7

The v2 run generated only the 100 v2 outputs under the frozen one-call protocol. The historical 17/100 and 39/100 totals are retained unchanged.
