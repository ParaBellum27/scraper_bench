"""Scoring boundaries that distinguish valid finance JSON from lookalikes."""
import unittest

from evaluator.grader import grade_case, summarize


class GraderTests(unittest.TestCase):
    def test_null_is_not_a_missing_field_or_zero(self):
        groups = {"returns": (1.0, ["irr"])}
        expected = {"irr": None}
        self.assertEqual(grade_case("null", expected, expected, scoring_groups=groups).score, 100)
        missing = grade_case("missing", {}, expected, scoring_groups=groups)
        self.assertEqual(missing.score, 0)
        self.assertEqual(missing.missing_fields, ["irr"])
        self.assertEqual(grade_case("zero", {"irr": 0}, expected, scoring_groups=groups).score, 0)

    def test_dates_are_exact_and_arrays_keep_partial_credit(self):
        groups = {"timing": (1.0, ["status", "dates"])}
        expected = {"status": "ok", "dates": ["2024-12-01", "2025-12-01"]}
        actual = {"status": "ok", "dates": ["2024-12-01", "2025-12-02"]}
        result = grade_case("date", actual, expected, scoring_groups=groups)
        self.assertEqual(result.score, 75)
        self.assertEqual(result.mismatches["dates"], {"bad_indices": [1]})
        actual["dates"] = ["2024-12-01"]
        self.assertEqual(grade_case("length", actual, expected, scoring_groups=groups).score, 50)

    def test_boolean_nonfinite_and_oversized_numbers_cannot_earn_numeric_credit(self):
        groups = {"cash": (1.0, ["cash"])}
        for value in (True, float("nan"), float("inf"), 10 ** 400):
            with self.subTest(value_type=type(value).__name__):
                result = grade_case("invalid", {"cash": value}, {"cash": 1}, scoring_groups=groups)
                self.assertEqual(result.score, 0)

    def test_selected_tolerances_do_not_change_default_tolerance(self):
        groups = {"cash": (1.0, ["cash"])}
        actual, expected = {"cash": 100.00002}, {"cash": 100.0}
        self.assertEqual(grade_case("default", actual, expected, scoring_groups=groups).score, 100)
        self.assertEqual(grade_case("strict", actual, expected, scoring_groups=groups,
                                    rel_tol=1e-7, abs_tol=1e-7).score, 0)

    def test_high_partial_score_is_not_reported_as_fully_correct(self):
        groups = {"value": (0.98, ["value"]), "return": (0.02, ["irr"])}
        expected = {"value": 100, "irr": 0.2}
        correct = grade_case("correct", expected, expected, scoring_groups=groups)
        wrong_return = grade_case("wrong_return", {"value": 100, "irr": 0.19}, expected, scoring_groups=groups)
        report = summarize(correct, [correct, wrong_return])
        self.assertEqual(wrong_return.score, 98)
        self.assertTrue(report["base_case_fully_correct"])
        self.assertEqual(report["hidden_cases_passed_95"], 2)
        self.assertEqual(report["hidden_cases_fully_correct"], 1)


if __name__ == "__main__":
    unittest.main()
