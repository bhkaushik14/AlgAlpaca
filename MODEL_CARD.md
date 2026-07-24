# AlgAlpaca model card

## Model

AlgAlpaca v2 uses a private PEFT QLoRA adapter with `codellama/CodeLlama-7b-Instruct-hf`, frozen base revision `22cb240e0292b0b5ab4c17ccd97aa3a2f799cbed`. It is not a standalone model.

V2 was produced by continuing QLoRA fine-tuning from the original AlgAlpaca adapter. It was not trained from the base model as a fresh adapter.

- LoRA rank 16, alpha 32, dropout 0.05, bias `none`.
- Targets: q/k/v/o and gate/up/down projections.
- Adapter parameters: 39,976,960.
- V2 adapter weight SHA-256: `a56735e268a5343a02966d3ad8513c2b4a6232b2ed97e9dcdfaa70404293215d`.
- V2 adapter config SHA-256: `67625139ecb7f71fee57be953ba8070a3f2f0981691038781747aa05b602e797`.
- Original adapter weight SHA-256: `4dfc1a875feccfdb7affd98326d63704b5cf0ec3509468ba505cd4978e5d02d3`.

The v2 adapter remains an external local artifact and has not been uploaded to Hugging Face. The historical private repository identifier `bhkaushik14/codellama-algebra-to-code-adapter` is retained only for original-adapter provenance and is not a claim of public access.

## Intended use

Controlled local educational and research use for algebra-to-Python/SymPy generation. It is not intended for high-stakes decisions, autonomous or public arbitrary-code execution, or production deployment.

## Training record

V2 used a 16,500-example executable, verified algebra-to-SymPy dataset covering 22 categories. The split contained 13,186 training examples, 1,677 validation examples, and 1,637 held-out test examples. Continued training ran for one epoch and 825 optimizer steps. The targets were complete executable programs with observable output.

The original adapter's surviving record supports 4-bit NF4 QLoRA-style supervised fine-tuning with mixed natural-language and program targets. Saved historical data comprised 82,269 source rows, split into 78,156 training and 4,113 validation rows. No training data is redistributed. Exact original dataset revisions, sampling ratios, the complete command, and some environment details remain unresolved.

## Evaluation

On the frozen 100-problem benchmark, automated correctness improved from 17% for the base model to 39% for the original adapter and 59% for v2. Manual review found 12 additional v2 outputs that were mathematically equivalent but rejected by the scorer, bringing reviewed mathematical correctness to 71%.

The 59/100 automated score is the apples-to-apples benchmark result. The 71/100 figure is a separate manual mathematical review, not automated benchmark accuracy. Executable output increased from 61/100 for the original adapter to 85/100 for v2. Paired original-v2 automated outcomes were both correct 28, original only 11, v2 only 31, and both incorrect 30.

The frozen 100-case fixture is separate from the 1,637-example test split. It was not used for v2 training, routine prompt tuning, or checkpoint tuning. Generated source was judged by execution and mathematical result, not similarity to reference source. See the [evaluation package](evaluation/README.md).

## Safety and limitations

After manual equivalence review, v2 still had 14 mathematically wrong answers, 8 execution failures, and 7 policy failures. System answers often used ordered tuple representations that the frozen scorer rejected, and some generated programs used invalid or non-allowlisted SymPy operations.

Generated programs require review. Execution success does not establish mathematical correctness. The AST policy and restricted subprocess provide defense in depth but are not hardened public containment. Results from one project-specific fixture do not establish broader mathematical performance or production readiness.

## Loading

After separately obtaining the governed base revision and private v2 adapter, set `.algalpaca-adapter-path` to the local checkpoint directory. The application verifies the v2 adapter file sizes, hashes, and PEFT configuration before local loading. See the [quick start](README.md#quick-start).

## Licensing

MIT applies only to project-owned source. It does not relicense Code Llama, the adapter, datasets, or other third-party material. See [licensing](docs/licensing.md).
