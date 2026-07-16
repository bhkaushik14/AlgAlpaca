import hashlib
import unittest

from codellama_algebra.compatible import (
    classify_response_format,
    extract_compatible_code,
    extract_direct_answer,
    parse_observable_stdout,
)
from codellama_algebra.sandbox import ExecutionStatus, execute_compatible_validated
from codellama_algebra.validation import ValidationResult, validate_code_compatible


class CompatibleExtractionTests(unittest.TestCase):
    def test_accepts_documented_fence_labels_and_preserves_source(self):
        cases = {
            "python": "explicit_python_fence",
            "PY": "python_alias_fence",
            "python3": "python_alias_fence",
            "": "unlabeled_markdown_fence",
        }
        for label, wrapper in cases.items():
            with self.subTest(label=label):
                raw = f"prose\n```{label}\r\n  result = 2 + 3\r\nprint(result)  \r\n```\nend"
                result = extract_compatible_code(raw)
                self.assertTrue(result.valid, result)
                self.assertEqual(result.wrapper_type, wrapper)
                self.assertEqual(result.code, "result = 2 + 3\nprint(result)")
                self.assertFalse(result.semantic_edits)
                self.assertEqual(
                    result.code_sha256,
                    hashlib.sha256(result.code.encode("utf-8")).hexdigest(),
                )
                self.assertEqual(raw[result.source_start : result.source_end].replace("\r\n", "\n"), result.code)

    def test_accepts_legacy_source_but_never_output_tag_as_source(self):
        accepted = extract_compatible_code(
            "intro\n<llm-code>\nvalue = 5\nprint(value)\n</llm-code>\n<llm-code-output>5</llm-code-output>"
        )
        self.assertTrue(accepted.valid)
        self.assertEqual(accepted.wrapper_type, "legacy_llm_code")
        rejected = extract_compatible_code("<llm-code-output>print(5)</llm-code-output>")
        self.assertFalse(rejected.valid)
        self.assertIsNone(rejected.code)

    def test_accepts_whole_raw_python_only_without_prose_or_wrappers(self):
        raw = extract_compatible_code("  value = 5\nprint(value)  ")
        self.assertTrue(raw.valid)
        self.assertEqual(raw.wrapper_type, "raw_python")
        self.assertEqual(raw.code, "value = 5\nprint(value)")
        for rejected in ("Here is code: print(5)", "```text\nprint(5)\n```", ""):
            with self.subTest(rejected=rejected):
                self.assertFalse(extract_compatible_code(rejected).valid)

    def test_rejects_multiple_plausible_blocks_and_unparseable_unlabeled_block(self):
        multiple = "```python\nprint(1)\n```\n```\nprint(2)\n```"
        self.assertEqual(
            extract_compatible_code(multiple).error_code,
            "ambiguous_code_blocks",
        )
        invalid = extract_compatible_code("```\nresult = (\n```")
        self.assertFalse(invalid.valid)

    def test_census_is_multilabel(self):
        classified = classify_response_format(
            "Explanation\n<llm-code>\nprint(2)\n</llm-code>"
        )
        self.assertEqual(classified.primary_category, "legacy_llm_code")
        self.assertIn("prose_with_inline_code", classified.labels)


class CompatiblePolicyAndExecutionTests(unittest.TestCase):
    def test_compatible_policy_relaxes_only_stdout_contract(self):
        self.assertTrue(validate_code_compatible("value = 2 + 3").valid)
        self.assertTrue(validate_code_compatible("print(1)\nprint(2)").valid)
        blocked = validate_code_compatible('value = open("x")')
        self.assertFalse(blocked.valid)
        self.assertEqual(blocked.error_code, "policy_violation")

    def test_execution_uses_exact_source_and_no_output_is_still_success(self):
        no_output = execute_compatible_validated(
            ValidationResult(True, "value = 2 + 3")
        )
        self.assertEqual(no_output.status, ExecutionStatus.OK)
        self.assertEqual(no_output.stdout, "")
        output = execute_compatible_validated(
            ValidationResult(True, 'print("diagnostic")\nprint("ANSWER:", 5)')
        )
        self.assertEqual(output.status, ExecutionStatus.OK)
        self.assertEqual(output.stdout, "diagnostic\nANSWER: 5\n")


class ObservableAndDirectAnswerTests(unittest.TestCase):
    def test_stdout_hierarchy(self):
        selected = parse_observable_stdout("debug\nANSWER: 5\n")
        self.assertEqual(selected.status, "observable")
        self.assertEqual(selected.answer, "5")
        self.assertEqual(selected.mode, "unique_answer_line")
        self.assertEqual(selected.diagnostic_lines, ("debug",))
        single = parse_observable_stdout("[1, 2]\n")
        self.assertEqual(single.answer, "[1, 2]")
        self.assertEqual(single.mode, "unique_nonempty_line")

    def test_stdout_never_uses_last_line_heuristic(self):
        self.assertEqual(parse_observable_stdout("").status, "no_output")
        self.assertEqual(parse_observable_stdout("one\ntwo\n").status, "ambiguous_stdout")
        self.assertEqual(
            parse_observable_stdout("ANSWER: 1\nANSWER: 2\n").status,
            "ambiguous_stdout",
        )

    def test_direct_answers_are_separate_and_unambiguous(self):
        direct = extract_direct_answer(
            "</llm-code-output>\n\nThe answer is \\boxed{15/2}."
        )
        self.assertTrue(direct.valid)
        self.assertEqual(direct.answer, "15/2")
        self.assertEqual(direct.mode, "boxed_answer")
        self.assertFalse(extract_direct_answer("```\nprint(5)\n```").valid)
        self.assertEqual(
            extract_direct_answer("\\boxed{1} and \\boxed{2}").error_code,
            "ambiguous_direct_answer",
        )


if __name__ == "__main__":
    unittest.main()
