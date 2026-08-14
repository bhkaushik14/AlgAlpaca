# History

The QLoRA adapter and original experiments predate the public AlgAlpaca repository. The surviving adapter, configuration, logs, and evaluation material were later examined to reconstruct a runnable local application and document the supported research claims.

V2 was trained later as a second-stage QLoRA continuation from the original adapter with Code Llama 7B as the frozen base. It used 16,500 execution-verified algebra-to-SymPy examples across 22 categories: 13,186 training examples, 1,677 validation examples, and 1,637 held-out test examples. The final continuation ran for one epoch and 825 optimizer steps.

The 1,637-example held-out dataset split and the frozen 100-case confirmatory benchmark are different evaluation sets. The benchmark was retained separately from the second-stage split and routine tuning. Preserved public artifacts do not demonstrate exhaustive semantic non-overlap between every benchmark problem and every generated training example.

Under the retained automated protocol, the base model scored 17/100, the original adapter scored 39/100, and v2 scored 59/100. Manual review counted 12 additional mathematically equivalent v2 outputs for a separate reviewed total of 71/100.

The public repository keeps the working application, exact confirmatory questions, retained base/original results, v2 per-case results, and code needed to validate fixture and scoring behavior. Training workspaces, checkpoints, duplicate raw-output files, and release-process audits remain outside this repository.

Some historical training details cannot be reconstructed exactly, including complete dataset revisions and sampling, the final training command, and parts of the software and hardware environment. The preserved confirmatory results do not depend on recreating that training run.
