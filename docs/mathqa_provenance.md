# MathQA provenance

Status: **EXACTLY IDENTIFIED**. Accessed 2026-07-14.

The 2,269 historical `MathQA_local` rows are an exact filtered subset of the official MathQA archive added in repository commit `e08abef77abe6004d2c0e1251d009b86d0c0b68f`. All four source files match the official archive byte-for-byte. No raw training row is included here.

## Reconstruction

The producing October 1, 2025 preprocessing versions were recovered from editor history and predate the saved outputs by minutes. They:

1. loaded the four JSON arrays in `challenge_test.json`, `dev.json`, `test.json`, `train.json` order;
2. mapped `Problem` to `prompt`, `Rationale` to `solution`, and `annotated_formula` to `program`, with source `MathQA_local`;
3. applied the recovered algebra predicate and a non-binding 30,000-row cap;
4. shuffled with Hugging Face Datasets/NumPy `default_rng`, seed 42;
5. wrote the first 1,000 shuffled rows to validation and the remaining 1,269 to training.

The retained split ancestry is 34 `challenge_test`, 287 `dev`, 189 `test`, and 1,759 `train` rows. There are 2,235 unique normalized field triples and 34 duplicate extra occurrences. Duplicate multiplicity was preserved.

## Match results

| Candidate | Candidate rows | Exact matches | Normalized-only | Unmatched | Result |
|---|---:|---:|---:|---:|---|
| Official MathQA archive | 37,901 | 2,269 | 0 | 0 | Exact canonical multiset and exact saved order reproduced |
| Official AQuA-RAT, commit `26b64ed1f22208c6742f47df547dfd65088ec30d` | 97,975 | 66 exact-question; 2,244 normalized question+rationale+correct | separately labeled fallback | 25 under that normalized composite | Confirms ancestry, not record identity |

The AQuA fallback normalization was Unicode NFKC, case-folding, then removal of non-alphanumeric characters. Its results are not counted as exact MathQA matches. MathQA describes itself as adding operation-program annotations over AQuA-RAT and correcting some rationales; the comparison supports that descendant relationship but also shows why the two releases must not be treated as interchangeable.

## Evidence boundaries

Private evidence contains SHA-256 fingerprints for every retained row and source candidate, exact source indices, duplicate accounting, file hashes, and retrieval records. This public summary intentionally contains no raw historical row, private path, cache path, or machine identifier.

## License consequence

Exact provenance resolves the former source-identity blocker. It does not resolve permission for MathQA-authored annotations. The repository-level MIT file is copyrighted by Blackrock Digital LLC and covers the website template; it was committed before the dataset archive and does not expressly grant rights from the MathQA authors in the downloadable records or operation annotations. AQuA-RAT's Apache-2.0 license covers its repository materials but does not automatically license independently created MathQA annotations.

Official sources: [MathQA site](https://math-qa.github.io/math-QA/), [MathQA repository](https://github.com/math-QA/math-QA), [AQuA-RAT repository](https://github.com/google-deepmind/AQuA), and [MathQA paper](https://arxiv.org/abs/1905.13319).
