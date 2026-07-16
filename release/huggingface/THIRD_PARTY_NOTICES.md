# Third-party notices

No dataset records are included in this adapter package.

## Code Llama / Llama 2

Copyright Meta Platforms, Inc. The complete Llama 2 Community License is in `LICENSE`; required attribution is in `NOTICE`; use must comply with the incorporated Acceptable Use Policy.

## MathQA and AQuA-RAT

Training used 2,269 filtered records exactly identified with the official MathQA archive. Cite Amini et al., “MathQA: Towards Interpretable Math Word Problem Solving with Operation-Based Formalisms” (2019). MathQA builds on AQuA-RAT; cite Ling et al., “Program Induction by Rationale Generation” (2017).

AQuA-RAT repository materials carry this notice: Copyright 2017 Google Inc. Licensed under the Apache License, Version 2.0. Official license: https://github.com/google-deepmind/AQuA/blob/master/LICENSE

The MathQA website repository's MIT file is a Blackrock Digital website-template license and is not represented here as a MathQA dataset/annotation license. Public adapter release remains blocked pending MathQA-author clarification.

## OpenMathInstruct-1

Training also used a filtered subset of NVIDIA OpenMathInstruct-1, revision `4627efae6bd2ddcebb8acac00d513ffd8e00775c`. Cite Toshniwal et al., “OpenMathInstruct-1: A 1.8 Million Math Instruction Tuning Dataset” (2024). The exact NVIDIA License follows so its complete terms travel with this package.

```text
NVIDIA License

1. Definitions

“Licensor” means any person or entity that distributes its Work.
“Work” means (a) the original work of authorship made available under this license, which may include software, documentation, or other files, and (b) any additions to or derivative works thereof that are made available under this license.
The terms “reproduce,” “reproduction,” “derivative works,” and “distribution” have the meaning as provided under U.S. copyright law; provided, however, that for the purposes of this license, derivative works shall not include works that remain separable from, or merely link (or bind by name) to the interfaces of, the Work.
Works are “made available” under this license by including in or with the Work either (a) a copyright notice referencing the applicability of this license to the Work, or (b) a copy of this license.

2. License Grant. Copyright Grant. Subject to the terms and conditions of this license, each Licensor grants to you a perpetual, worldwide, non-exclusive, royalty-free, copyright license to use, reproduce, prepare derivative works of, publicly display, publicly perform, sublicense and distribute its Work and any resulting derivative works in any form.

3. Limitations

3.1 Redistribution. You may reproduce or distribute the Work only if (a) you do so under this license, (b) you include a complete copy of this license with your distribution, and (c) you retain without modification any copyright, patent, trademark, or attribution notices that are present in the Work.

3.2 Derivative Works. You may specify that additional or different terms apply to the use, reproduction, and distribution of your derivative works of the Work (“Your Terms”) only if (a) Your Terms provide that the use limitation in Section 3.3 applies to your derivative works, and (b) you identify the specific derivative works that are subject to Your Terms. Notwithstanding Your Terms, this license (including the redistribution requirements in Section 3.1) will continue to apply to the Work itself.

3.3 Patent Claims. If you bring or threaten to bring a patent claim against any Licensor (including any claim, cross-claim or counterclaim in a lawsuit) to enforce any patents that you allege are infringed by any Work, then your rights under this license from such Licensor (including the grant in Section 2.1) will terminate immediately.

3.4 Trademarks. This license does not grant any rights to use any Licensor’s or its affiliates’ names, logos, or trademarks, except as necessary to reproduce the notices described in this license.

3.5 Termination. If you violate any term of this license, then your rights under this license (including the grant in Section 2.1) will terminate immediately.

4. Disclaimer of Warranty. THE WORK IS PROVIDED “AS IS” WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, EITHER EXPRESS OR IMPLIED, INCLUDING WARRANTIES OR CONDITIONS OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, TITLE OR NON-INFRINGEMENT. YOU BEAR THE RISK OF UNDERTAKING ANY ACTIVITIES UNDER THIS LICENSE. 

5. Limitation of Liability. EXCEPT AS PROHIBITED BY APPLICABLE LAW, IN NO EVENT AND UNDER NO LEGAL THEORY, WHETHER IN TORT (INCLUDING NEGLIGENCE), CONTRACT, OR OTHERWISE SHALL ANY LICENSOR BE LIABLE TO YOU FOR DAMAGES, INCLUDING ANY DIRECT, INDIRECT, SPECIAL, INCIDENTAL, OR CONSEQUENTIAL DAMAGES ARISING OUT OF OR RELATED TO THIS LICENSE, THE USE OR INABILITY TO USE THE WORK (INCLUDING BUT NOT LIMITED TO LOSS OF GOODWILL, BUSINESS INTERRUPTION, LOST PROFITS OR DATA, COMPUTER FAILURE OR MALFUNCTION, OR ANY OTHER DAMAGES OR LOSSES), EVEN IF THE LICENSOR HAS BEEN ADVISED OF THE POSSIBILITY OF SUCH DAMAGES.
```

## Underlying OpenMathInstruct-1 problem sources

The official OpenMathInstruct-1 card identifies GSM8K and MATH training subsets as the problem sources.

- GSM8K: Copyright (c) 2021 OpenAI; MIT License; https://github.com/openai/grade-school-math/blob/master/LICENSE
- MATH: Copyright (c) 2021 Dan Hendrycks; MIT License; https://github.com/hendrycks/math/blob/master/LICENSE

These notices disclose training provenance. No GSM8K, MATH, OpenMathInstruct-1, MathQA, or AQuA-RAT record is redistributed.
