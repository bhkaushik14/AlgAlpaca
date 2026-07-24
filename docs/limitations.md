# Limitations

- V2 automated correctness was 59/100. Manual equivalence review reached 71/100, but that is not automated benchmark accuracy and remains too low for unverified use.
- V2 still had 14 mathematically wrong answers, 8 execution failures, and 7 policy failures after manual review. System tuple representation and execution-safe generation remain weak points.
- Generated code can be wrong. Execution is not correctness; no-output programs receive no credit.
- The frozen fixture is project-specific; three conditions on one fixture support no external-benchmark, population, inferential-statistical, or production claim.
- Original training data, revisions, preprocessing, program ratio, gradient checkpointing, and exact reproducibility remain uncertain. V2's 16,500-example second-stage dataset and split are documented separately.
- The private external adapter requires the governed base and is not a standalone 7B model. V2 has not been uploaded to Hugging Face.
- AST filtering and the local subprocess are not hardened public/multi-tenant containment; no public arbitrary-code execution is intended.
- Notation, assumptions, representations, source-data bias, and out-of-domain inputs can cause domain failures.
- Educational/research use only; independent mathematical and security review is required.
