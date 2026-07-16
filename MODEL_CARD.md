# AlgAlpaca model card

## Model

AlgAlpaca uses a private PEFT QLoRA adapter with `codellama/CodeLlama-7b-Instruct-hf`, frozen base revision `22cb240e0292b0b5ab4c17ccd97aa3a2f799cbed`. It is not a standalone model.

- LoRA rank 16, alpha 32, dropout 0.05, bias `none`.
- Targets: q/k/v/o and gate/up/down projections.
- Adapter parameters: 39,976,960.
- Adapter weight SHA-256: `4dfc1a875feccfdb7affd98326d63704b5cf0ec3509468ba505cd4978e5d02d3`.
- Adapter config SHA-256: `6ba240b6e47b51d102d7cfa4b763ceac4e91cdabb38f2967b20df36fb6f69c33`.

The adapter repository identifier is `bhkaushik14/codellama-algebra-to-code-adapter`. It is retained for provenance and is not a claim of public access.

## Intended use

Controlled local educational and research use for algebra-to-Python/SymPy generation. It is not intended for high-stakes decisions, autonomous or public arbitrary-code execution, or production deployment.

## Training record

The surviving record supports 4-bit NF4 QLoRA-style supervised fine-tuning with mixed natural-language and program targets. Saved data comprised 82,269 source rows, split into 78,156 training and 4,113 validation rows. No historical data is redistributed. Exact dataset revisions, sampling ratios, the complete command, and some environment details are unresolved.

## Evaluation

The base model scored 17/100 and the adapter scored 39/100 on the preserved confirmatory fixture. Paired outcomes were adapter-only 27, base-only 5, both correct 12, and both incorrect 56. Generated source was judged by execution and mathematical equivalence, not similarity to reference source. See the [evaluation package](evaluation/README.md).

## Safety and limitations

Generated programs can be invalid or wrong. Execution success does not establish mathematical correctness. The AST policy and restricted subprocess provide defense in depth but are not hardened public containment. Results from one fixture do not establish broader mathematical performance.

## Loading

After separately obtaining the governed base revision and private adapter, the application verifies adapter file sizes and hashes before local loading. See the [quick start](README.md#quick-start).

## Licensing

MIT applies only to project-owned source. It does not relicense Code Llama, the adapter, datasets, or other third-party material. See [licensing](docs/licensing.md).
