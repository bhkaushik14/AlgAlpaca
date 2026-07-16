# Licensing and adapter status

Reviewed 2026-07-14. This is a technical documentation review, not legal advice.

## Current status

- Hugging Face owner: `bhkaushik14`.
- Private model repository: `bhkaushik14/codellama-algebra-to-code-adapter`.
- Verified private repository revision: `f45496841d9fa96756f42d9133998ebf6715ae08`.
- Public adapter release is not authorized.
- The user reports accepting the applicable Code Llama terms through the Hugging Face account. This was not independently verified.

The private repository contains only the adapter weights and configuration plus the reviewed README, license, notice, and third-party notices. No dataset rows or base-model weights are included, and this document does not present the private repository as a public download.

## Source-by-source conclusions

| Material | Official source/revision | License text says | Text does not settle | Release treatment |
|---|---|---|---|---|
| CodeLlama-7B-Instruct | `codellama/CodeLlama-7b-Instruct-hf`, revision `22cb240e0292b0b5ab4c17ccd97aa3a2f799cbed` | Llama 2 Community License permits use/reproduction/distribution of Llama Materials and derivatives subject to its conditions | It does not name PEFT adapters separately | Treat adapter conservatively as derivative Llama Material |
| MathQA | Official archive, repository commit `e08abef77abe6004d2c0e1251d009b86d0c0b68f` | Site explains annotations over AQuA-RAT; paper/site request citation | No MathQA-author license grant for dataset records or operation annotations was found | Public release blocked pending narrow author clarification |
| MathQA repository MIT file | `math-QA/math-QA`, license commit `2204701ae1f6131faee330cca03f83e972ec35b0` | MIT terms for “software and associated documentation” copyrighted 2013–2019 Blackrock Digital LLC | Does not identify MathQA authors, dataset, or annotations; archive was added later | Do not label MathQA data MIT on this evidence |
| AQuA-RAT | `google-deepmind/AQuA`, commit `26b64ed1f22208c6742f47df547dfd65088ec30d` | Apache-2.0 notice applies to repository; permits use, modification, and distribution subject to license/notice rules | Does not grant rights in later MathQA annotations | Attribute AQuA-RAT; preserve Apache notice conservatively |
| OpenMathInstruct-1 | `nvidia/OpenMathInstruct-1`, exact cached revision `4627efae6bd2ddcebb8acac00d513ffd8e00775c` | NVIDIA License grants use, reproduction, derivative works, sublicensing, and distribution; redistribution requires its license and unchanged notices; derivative terms must preserve §3.3 | Does not state whether trained model weights are derivative works | No blocker; include NVIDIA attribution/license reference and do not redistribute rows |
| GSM8K | `openai/grade-school-math`, official repository | MIT permits use, modification, distribution, sublicensing, and sale with notice retention | Does not classify trained weights | Attribute as underlying OMI problem source |
| MATH | `hendrycks/math`, official repository | MIT permits use, modification, distribution, sublicensing, and sale with notice retention | Does not classify trained weights | Attribute as underlying OMI problem source |

OpenMathInstruct-1's exact-revision card states that questions come only from GSM8K and MATH training subsets and generated solutions were produced with Mixtral. NVIDIA also released multiple models trained on the dataset. Those model releases support an inference about intended model-training use, but the NVIDIA License—not release practice—is the governing text.

## Explicit Code Llama conditions

For any private or public adapter copy:

- include the complete Llama 2 Community License in `LICENSE`;
- retain this exact `NOTICE` sentence: “Llama 2 is licensed under the LLAMA 2 Community License, Copyright (c) Meta Platforms, Inc. All Rights Reserved.”;
- identify the base model and frozen revision;
- comply with the incorporated Llama 2 Acceptable Use Policy and applicable law;
- do not use Llama Materials or their output to improve another large language model other than Llama 2 or its derivatives;
- comply with the 700-million-monthly-active-user commercial threshold if it ever applies;
- use Meta marks only as reasonably necessary for attribution.

The Hugging Face license metadata is `llama2`. The repository MIT license does not apply to the adapter.

## Dataset terms versus trained weights

None of the MathQA, AQuA-RAT, NVIDIA, GSM8K, or MATH texts inspected expressly classifies trained model weights as a derivative work. Therefore statements that the adapter definitely is—or definitely is not—a derivative of training data would be legal conclusions not supplied by the texts.

The private package discloses the training sources, includes the NVIDIA and AQuA notices, and contains no dataset rows. This does not supply the missing MathQA-author permission.

## Public-release blocker

The adapter remains private. Public release requires a MathQA author or authorized maintainer to confirm that the downloadable program annotations may be used to train a model and that resulting adapter weights may be publicly distributed when no dataset rows are included, or to identify the license and conditions that permit it.

Keeping the repository private does not resolve the underlying licensing question. The source analysis and official references below are retained so that any future release decision can be reviewed against the same evidence.

## Official sources

- [Code Llama repository and model documentation](https://github.com/meta-llama/codellama)
- [Frozen base Llama 2 license](https://huggingface.co/codellama/CodeLlama-7b-Instruct-hf/blob/22cb240e0292b0b5ab4c17ccd97aa3a2f799cbed/LICENSE)
- [Llama 2 Acceptable Use Policy](https://github.com/meta-llama/llama/blob/main/USE_POLICY.md)
- [Hugging Face accepted license identifiers](https://huggingface.co/docs/hub/repositories-licenses)
- [MathQA site](https://math-qa.github.io/math-QA/) and [repository](https://github.com/math-QA/math-QA)
- [AQuA-RAT repository and license](https://github.com/google-deepmind/AQuA)
- [OpenMathInstruct-1 card](https://huggingface.co/datasets/nvidia/OpenMathInstruct-1) and [NVIDIA License](https://huggingface.co/datasets/nvidia/OpenMathInstruct-1/blob/main/LICENSE)
- [GSM8K](https://github.com/openai/grade-school-math) and [MATH](https://github.com/hendrycks/math)
