import unittest
from types import SimpleNamespace
from unittest.mock import patch

from codellama_algebra.generation import GenerationConfig, generate_problem
from codellama_algebra.prompts import REPAIR_PROMPT_VERSION


VALID_RESPONSE = '```python\nresult = 2\nprint("ANSWER:", result)\n```'


class _Tokenizer:
    def apply_chat_template(self, messages, **kwargs):
        return f"rendered:{messages[-1]['content']}"


class GenerationTests(unittest.TestCase):
    def setUp(self):
        self.loaded = SimpleNamespace(tokenizer=_Tokenizer(), model=object())

    def test_valid_response_is_not_repaired_and_is_timed(self):
        with patch("codellama_algebra.generation.generate_raw", return_value=VALID_RESPONSE):
            result = generate_problem(self.loaded, "Solve x + 1 = 3")
        self.assertFalse(result.repair_used)
        self.assertIsNone(result.repair_prompt_version)
        self.assertEqual(len(result.attempts), 1)
        self.assertGreaterEqual(result.attempts[0].duration_seconds, 0)
        self.assertTrue(result.validation.valid)

    def test_invalid_format_gets_exactly_one_repair(self):
        with patch(
            "codellama_algebra.generation.generate_raw",
            side_effect=["result = 2", VALID_RESPONSE],
        ) as generate:
            result = generate_problem(self.loaded, "Solve x + 1 = 3")
        self.assertTrue(result.repair_used)
        self.assertEqual(result.repair_prompt_version, REPAIR_PROMPT_VERSION)
        self.assertEqual(len(result.attempts), 2)
        self.assertEqual(generate.call_count, 2)
        self.assertTrue(result.validation.valid)

    def test_token_limits_must_be_positive(self):
        with self.assertRaises(ValueError):
            GenerationConfig(max_input_tokens=0)
        with self.assertRaises(ValueError):
            GenerationConfig(max_new_tokens=0)


if __name__ == "__main__":
    unittest.main()
