import unittest

from codellama_algebra.sandbox import (
    ExecutionLimits,
    ExecutionStatus,
    _execute_approved_code,
    execute_response,
    execute_validated,
)
from codellama_algebra.validation import ValidationResult


class SandboxTests(unittest.TestCase):
    def test_valid_execution(self):
        response = '```python\nresult = 3/2\nprint("ANSWER:", result)\n```'
        result = execute_response(response)
        self.assertEqual(result.status, ExecutionStatus.OK, result)
        self.assertEqual(result.answer, "1.5")

    def test_policy_failure_prevents_execution(self):
        response = '```python\nresult = open("x")\nprint("ANSWER:", result)\n```'
        result = execute_response(response)
        self.assertEqual(result.status, ExecutionStatus.POLICY_FAILURE)
        self.assertIsNone(result.returncode)

    def test_forged_validation_is_rechecked(self):
        forged = ValidationResult(True, 'result = open("x")\nprint("ANSWER:", result)')
        result = execute_validated(forged)
        self.assertEqual(result.status, ExecutionStatus.POLICY_FAILURE)

    def test_timeout_behavior(self):
        limits = ExecutionLimits(wall_seconds=0.2, cpu_seconds=1)
        result = _execute_approved_code("while True:\n    pass\n", limits)
        self.assertEqual(result.status, ExecutionStatus.TIMEOUT, result)
        self.assertTrue(result.timed_out)

    def test_nonzero_process_exit(self):
        result = _execute_approved_code("raise RuntimeError('synthetic')", ExecutionLimits())
        self.assertEqual(result.status, ExecutionStatus.NONZERO_EXIT)
        self.assertNotEqual(result.returncode, 0)

    def test_stdout_limit(self):
        limits = ExecutionLimits(stdout_bytes=128)
        result = _execute_approved_code('print("ANSWER:", "x" * 10000)', limits)
        self.assertEqual(result.status, ExecutionStatus.EXCESSIVE_OUTPUT, result)
        self.assertTrue(result.output_truncated)

    def test_missing_answer(self):
        result = _execute_approved_code("print('hello')", ExecutionLimits())
        self.assertEqual(result.status, ExecutionStatus.MISSING_ANSWER)

    def test_multiple_answer_lines(self):
        code = "print('ANSWER:', 1)\nprint('ANSWER:', 2)"
        result = _execute_approved_code(code, ExecutionLimits())
        self.assertEqual(result.status, ExecutionStatus.MULTIPLE_ANSWERS)

    def test_extra_output_is_malformed(self):
        code = "print('debug')\nprint('ANSWER:', 2)"
        result = _execute_approved_code(code, ExecutionLimits())
        self.assertEqual(result.status, ExecutionStatus.MALFORMED_OUTPUT)


if __name__ == "__main__":
    unittest.main()
