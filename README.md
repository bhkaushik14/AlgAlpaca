# AlgAlpaca

## Overview

AlgAlpaca is a local application built around a QLoRA adapter fine-tuned from Code Llama. It takes an algebra problem, generates Python/SymPy code, runs the code locally, and displays the generated program and result.

The adapter is not included. It must be supplied from an authorized private local copy and used with `codellama/CodeLlama-7b-Instruct-hf` revision `22cb240e0292b0b5ab4c17ccd97aa3a2f799cbed`.

## What it does

- Accepts an algebra problem in the browser.
- Generates a Python/SymPy program with the locally configured adapter.
- Extracts code, validates syntax, and applies an AST-based execution policy.
- Runs accepted code in a restricted subprocess with time and resource limits.
- Displays the generated program and result, including concise failure details.

## Interface

The React interface provides a workspace, examples, evaluation results, documentation, and local model status. FastAPI serves the built frontend and local API. Model loading remains lazy: startup and configuration checks do not load model weights.

## Results

On the 100-case confirmatory evaluation, the base model solved 17/100 cases and the fine-tuned adapter solved 39/100. Paired outcomes were adapter-only 27, base-only 5, both correct 12, and both incorrect 56.

Fine-tuning improved performance under this evaluation, but the adapter remained unreliable: it failed 61 of 100 cases. The result applies only to this fixture, prompt, and scoring method.

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

Edit `.algalpaca-adapter-path` to contain the absolute path to the authorized local adapter directory. Adapter weights are private and must be supplied locally. The required Code Llama base revision must be locally available or downloadable by an authorized user. With an already populated cache, optional offline execution can use `HF_HUB_OFFLINE=1`.

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

The application formats the fixed inference prompt, performs one model generation, extracts a candidate program, rejects syntax or policy violations, executes accepted code under subprocess restrictions, and presents the program and bounded output. See [architecture](docs/architecture.md).

## Repository map

- `src/codellama_algebra/`: inference, extraction, policy, execution, scoring, and API code.
- `frontend/`: React/TypeScript interface.
- `demo/`: local Gradio fallback and illustrative cases.
- `tests/`: functional application and evaluation tests.
- `evaluation/`: frozen fixture, compact results, methodology, and offline validators.
- `docs/`: architecture, history, limitations, licensing, and provenance notes.
- `release/huggingface/`: applicable license and third-party notices retained for the private adapter.

## Limitations

Confirmatory accuracy was 39%. Outputs are prompt-sensitive and may be invalid or mathematically incorrect, with particular difficulty on domains and inequalities. The execution controls reduce risk but are not hardened for public multi-user arbitrary-code execution. The historical training environment cannot be reconstructed exactly. See [limitations](docs/limitations.md).

## History

The adapter and original experiments predate this public repository. The project was later reconstructed into a runnable local application and compact evaluation package. Some historical training details remain incomplete; see [history](docs/history.md).

## Links

- [AlgAlpaca on GitHub](https://github.com/bhkaushik14/AlgAlpaca)
- [Evaluation methodology and results](evaluation/README.md)
- [Model card](MODEL_CARD.md)
- [Licensing](docs/licensing.md)
