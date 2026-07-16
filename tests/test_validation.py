import unittest

from codellama_algebra.validation import extract_python_block, validate_code, validate_response


VALID = '''```python
import sympy as sp
x = sp.symbols("x")
result = sp.solve(sp.Eq(2*x + 1, 5), x)
print("ANSWER:", result)
```'''


class ValidationTests(unittest.TestCase):
    def test_one_valid_fenced_block(self):
        result = validate_response(VALID)
        self.assertTrue(result.valid, result)
        self.assertIn("sp.solve", result.code)

    def test_no_fenced_block(self):
        result = extract_python_block("print('ANSWER:', 2)")
        self.assertEqual(result.error_code, "no_code_block")

    def test_multiple_fenced_blocks(self):
        result = extract_python_block("```python\na=1\n```\n```python\nb=2\n```")
        self.assertEqual(result.error_code, "multiple_code_blocks")

    def test_malformed_fence(self):
        result = extract_python_block("```python\nprint('ANSWER:', 2)")
        self.assertEqual(result.error_code, "malformed_fence")

    def test_surrounding_prose(self):
        result = extract_python_block("Here is code:\n" + VALID)
        self.assertEqual(result.error_code, "surrounding_text")

    def test_valid_python_syntax(self):
        result = validate_code('result = 2 + 3\nprint("ANSWER:", result)')
        self.assertTrue(result.valid, result.violations)

    def test_syntax_error(self):
        result = validate_code('result = (\nprint("ANSWER:", result)')
        self.assertEqual(result.error_code, "syntax_error")

    def test_allowed_sympy_from_imports(self):
        code = (
            "from sympy import Eq, solve, symbols\n"
            "x = symbols('x')\n"
            "result = solve(Eq(x + 1, 3), x)\n"
            'print("ANSWER:", result)'
        )
        self.assertTrue(validate_code(code).valid)

    def test_blocked_imports(self):
        for module in ("os", "sys", "subprocess", "socket", "pathlib", "multiprocessing"):
            with self.subTest(module=module):
                result = validate_code(f'import {module}\nprint("ANSWER:", 1)')
                self.assertFalse(result.valid)
                self.assertIn("import", " ".join(result.violations))

    def test_blocked_builtins(self):
        for call in (
            "open('x')",
            "eval('1')",
            "exec('x=1')",
            "compile('1', '<x>', 'eval')",
            "input()",
            "__import__('os')",
        ):
            with self.subTest(call=call):
                result = validate_code(f'result = {call}\nprint("ANSWER:", result)')
                self.assertFalse(result.valid)

    def test_sympify_is_not_allowlisted(self):
        code = 'from sympy import sympify\nresult = sympify("1")\nprint("ANSWER:", result)'
        self.assertFalse(validate_code(code).valid)

    def test_dunder_access(self):
        result = validate_code('result = (1).__class__\nprint("ANSWER:", result)')
        self.assertFalse(result.valid)
        self.assertIn("dunder", " ".join(result.violations))

    def test_reflection_attempts(self):
        for expression in ("getattr(1, 'real')", "vars()", "dir(1)", "type(1)"):
            with self.subTest(expression=expression):
                result = validate_code(f'result = {expression}\nprint("ANSWER:", result)')
                self.assertFalse(result.valid)

    def test_definitions_and_lambdas_are_blocked(self):
        function = 'def f():\n    return 1\nresult = 1\nprint("ANSWER:", result)'
        lambda_code = 'result = (lambda x: x)(1)\nprint("ANSWER:", result)'
        self.assertFalse(validate_code(function).valid)
        self.assertFalse(validate_code(lambda_code).valid)


if __name__ == "__main__":
    unittest.main()
