# AlgAlpaca

## Overview

AlgAlpaca is a local application built around a QLoRA adapter for Code Llama. It takes an algebra problem, generates Python/SymPy code, runs the code locally, and displays the generated program and result.

V2 was produced by continued QLoRA fine-tuning from the original adapter on 16,500 executable, verified algebra-to-SymPy examples spanning 22 categories.

On the frozen 100-problem benchmark, automated correctness improved from 17% for the base model to 39% for the original adapter and 59% for v2. Manual review found 12 additional v2 outputs that were mathematically equivalent but rejected by the scorer, bringing reviewed mathematical correctness to 71%.

| Condition | Automated correct | Executable output |
|---|---:|---:|
| Base model | 17/100 | 38/100 |
| Original adapter | 39/100 | 61/100 |
| V2 adapter | **59/100** | **85/100** |

The 59/100 automated result is the direct comparison with the retained 17/100 and 39/100 scores. The 71/100 figure is reported separately after manual equivalence review.

The adapter is not included in this repository. It must be supplied from an authorized private local copy and used with `codellama/CodeLlama-7b-Instruct-hf` revision `22cb240e0292b0b5ab4c17ccd97aa3a2f799cbed`.

## What it does

- Accepts an algebra problem in the browser.
- Generates a Python/SymPy program with the locally configured adapter.
- Extracts code, validates syntax, and applies an AST-based execution policy.
- Runs accepted code in a restricted subprocess with time and resource limits.
- Displays the generated program and result, including concise failure details.

## Interface

The React interface provides a workspace, examples, evaluation results, documentation, and local model status. FastAPI serves the built frontend and local API. Model loading remains lazy: startup and configuration checks do not load model weights.

## Results

V2 produced 59 automated-correct answers and 85 executable programs. The original adapter produced 39 automated-correct answers and 61 executable programs under the same frozen protocol.

Against the original adapter, paired automated outcomes were both correct 28, original only 11, v2 only 31, and both incorrect 30. The [evaluation comparison](evaluation/comparison.md) gives category and failure-stage details.

V2 is still not reliable enough for unsupervised use. After manual review, 14 answers remained mathematically wrong; another 8 failed during execution and 7 were rejected by the execution policy. In six system cases, v2 printed mathematically equivalent ordered tuples that the scorer did not map to named variables. The other four system cases were wrong or failed during execution.

## Quick start

AlgAlpaca supports Python 3.10 and 3.11. Use an existing compatible PyTorch/CUDA setup when possible; creating a fresh environment does not guarantee GPU compatibility.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[web]"
cd frontend
npm ci
npm run build
cd ..
cp .algalpaca-adapter-path.example .algalpaca-adapter-path
```

Edit `.algalpaca-adapter-path` to contain the absolute path to the authorized local v2 adapter directory. This ignored file tells the app where to find the adapter; the runtime still requires the fixed v2 sizes, hashes, and PEFT configuration. The private weights remain outside Git and must be supplied locally.

The required Code Llama base revision must be locally available or downloadable by an authorized user. With an already populated cache, optional offline execution can use `HF_HUB_OFFLINE=1`.

PyTorch and CUDA installation is machine-specific; this repository does not replace either. Then check and launch:

```bash
./run-algalpaca --check
./run-algalpaca
```

Open `http://127.0.0.1:8000`. The check command validates local configuration without loading or calling the model.

## Architecture

```text
prompt → model generation → code extraction → policy checks → subprocess execution → result presentation
```

The application formats the fixed inference prompt, performs one model generation, extracts a candidate program, rejects syntax or policy violations, executes accepted code under subprocess restrictions, and presents the program and bounded output.

The repository contains the application and evaluation artifacts. The selected adapter remains an external local artifact configured through `.algalpaca-adapter-path`. See [architecture](docs/architecture.md).

## Repository map

- `src/codellama_algebra/`: inference, extraction, policy, execution, scoring, and API code.
- `frontend/`: React/TypeScript interface.
- `demo/`: local Gradio fallback and illustrative cases.
- `tests/`: functional application and evaluation tests.
- `evaluation/`: frozen fixture, retained base/original results, v2 per-case results, methodology, comparison, and offline validators.
- `docs/`: architecture, history, limitations, licensing, and provenance notes.
- `release/huggingface/`: applicable license and third-party notices retained for the private adapter.

## Limitations

V2 automated correctness is 59/100, not 71/100; the larger number includes clear manual equivalence judgments. Seven policy failures, eight execution failures, and fourteen remaining mathematical errors show that generated programs still require review. The execution controls reduce risk but are not hardened for public multi-user arbitrary-code execution. See [limitations](docs/limitations.md).

## History

The original adapter and experiments predate this public repository. V2 is a second-stage continuation from that adapter, while the repository remains the home of the local application and compact evaluation package. Some original training details remain incomplete; see [history](docs/history.md).

## Links

- [AlgAlpaca on GitHub](https://github.com/bhkaushik14/AlgAlpaca)
- [Evaluation methodology and results](evaluation/README.md)
- [Three-model comparison](evaluation/comparison.md)
- [V2 per-case results](evaluation/v2_case_results.csv)
- [Model card](MODEL_CARD.md)
- [Licensing](docs/licensing.md)
