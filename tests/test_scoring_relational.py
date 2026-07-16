import unittest

from codellama_algebra.scoring import ExpectedAnswer, score_answer


class RelationalIntervalScoringTests(unittest.TestCase):
    def test_relational_interval_forms_are_converted_to_sets(self):
        cases = (
            (
                "(2 <= x) & (x < oo)",
                "Interval(2, oo)",
            ),
            (
                "(-2 < x) & (x < 2)",
                "Interval.open(-2, 2)",
            ),
            (
                "((1 <= x) & (x < oo)) | ((-oo < x) & (x <= -3))",
                "Union(Interval(-oo, -3), Interval(1, oo))",
            ),
        )
        for actual, expected_value in cases:
            with self.subTest(actual=actual):
                expected = ExpectedAnswer("interval_set", expected_value, ("x",))
                result = score_answer(actual, expected)
                self.assertTrue(result.correct, result)

    def test_relational_syntax_is_not_enabled_for_other_answer_kinds(self):
        expected = ExpectedAnswer("symbolic_expression", "x", ("x",))
        result = score_answer("x < 2", expected)
        self.assertFalse(result.correct)
        self.assertEqual(result.error_code, "malformed_answer")

    def test_relational_form_cannot_introduce_unknown_variables(self):
        expected = ExpectedAnswer("interval_set", "Interval(2, oo)", ("x",))
        result = score_answer("(2 <= y) & (y < oo)", expected)
        self.assertFalse(result.correct)
        self.assertEqual(result.error_code, "malformed_answer")


if __name__ == "__main__":
    unittest.main()
