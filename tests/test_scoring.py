import unittest

from codellama_algebra.scoring import ExpectedAnswer, score_answer


class ScoringTests(unittest.TestCase):
    def test_exact_number(self):
        expected = ExpectedAnswer("exact_number", "3/2")
        self.assertTrue(score_answer("1.5", expected).correct)

    def test_symbolic_expression(self):
        expected = ExpectedAnswer("symbolic_expression", "(x + 1)**2", ("x",))
        self.assertTrue(score_answer("x**2 + 2*x + 1", expected).correct)

    def test_finite_set_order_independent(self):
        expected = ExpectedAnswer("finite_set", ["-2", "1/2"], ("x",))
        self.assertTrue(score_answer("[1/2, -2]", expected).correct)

    def test_system_variable_mapping(self):
        expected = ExpectedAnswer("variable_mapping", {"x": "3", "y": "2"}, ("x", "y"))
        self.assertTrue(score_answer("{y: 2, x: 3}", expected).correct)
        self.assertTrue(score_answer("[{x: 3, y: 2}]", expected).correct)

    def test_interval(self):
        expected = ExpectedAnswer("interval_set", "Interval.open(-2, 2)", ("x",))
        self.assertTrue(score_answer("Interval.open(-2, 2)", expected).correct)

    def test_union_interval(self):
        value = "Union(Interval(-oo, -3), Interval(1, oo))"
        expected = ExpectedAnswer("interval_set", value, ("x",))
        self.assertTrue(score_answer(value, expected).correct)

    def test_approximate_value(self):
        expected = ExpectedAnswer("approximate_numeric", "sqrt(2)", tolerance=1e-5)
        self.assertTrue(score_answer("1.41421", expected).correct)

    def test_incorrect_answer(self):
        expected = ExpectedAnswer("exact_number", "4")
        result = score_answer("5", expected)
        self.assertFalse(result.correct)
        self.assertEqual(result.error_code, "incorrect_answer")

    def test_malformed_answer(self):
        expected = ExpectedAnswer("exact_number", "4")
        result = score_answer("open('/tmp/x')", expected)
        self.assertFalse(result.correct)
        self.assertEqual(result.error_code, "malformed_answer")

    def test_rational_exclusions_and_extraneous_solution(self):
        expected = ExpectedAnswer(
            "finite_set",
            ["7/2"],
            ("x",),
            domain_exclusions=("2",),
        )
        self.assertTrue(score_answer("{7/2}", expected).correct)
        self.assertFalse(score_answer("{2, 7/2}", expected).correct)


if __name__ == "__main__":
    unittest.main()
