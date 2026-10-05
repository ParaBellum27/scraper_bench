"""Scoring boundaries that distinguish valid finance JSON from lookalikes."""
import unittest
import json
from pathlib import Path

from evaluator.grader import grade_case, summarize
from evaluator.pierre_lbo_cases import exercised_features, generate_hidden_cases
from reference.pierre_lbo.reference import value_lbo


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
        self.assertEqual(report["hidden_cases_fully_correct"], 1)
        self.assertFalse(report["all_hidden_cases_correct"])
        self.assertFalse(report["all_cases_correct"])

    def test_all_hidden_cases_does_not_hide_base_failure_or_empty_suite(self):
        groups = {"cash": (1.0, ["cash"])}
        good = grade_case("good", {"cash": 1}, {"cash": 1}, scoring_groups=groups)
        bad = grade_case("bad", {}, {"cash": 1}, scoring_groups=groups)
        self.assertTrue(summarize(good, [good])["all_cases_correct"])
        base_failure = summarize(bad, [good])
        self.assertTrue(base_failure["all_hidden_cases_correct"])
        self.assertFalse(base_failure["all_cases_correct"])
        self.assertFalse(summarize(good, [])["all_hidden_cases_correct"])

    def test_insignificant_numeric_differences_do_not_fail_correctness(self):
        expected = {"cash": 1e8, "zero": 0.0, "irr": 0.1, "balances": [0.0, 10.0]}
        actual = {"cash": 1e8 + 1, "zero": 5e-8, "irr": 0.1 + 5e-8, "balances": [5e-8, 10.0]}
        groups = {"finance": (1.0, list(expected))}
        result = grade_case("roundoff", actual, expected, scoring_groups=groups, rel_tol=1e-7, abs_tol=1e-7)
        self.assertFalse(result.mismatches)
        self.assertTrue(summarize(result, [result])["all_cases_correct"])
        actual["balances"][1] = 10.001
        wrong = grade_case("wrong_balance", actual, expected, scoring_groups=groups, rel_tol=1e-7, abs_tol=1e-7)
        self.assertFalse(summarize(result, [wrong])["all_hidden_cases_correct"])

    def test_features_distinguish_failed_obligations_from_executed_repayments(self):
        base = json.loads((Path(__file__).resolve().parents[1] / "tasks/pierre_lbo/inputs/base_case.json").read_text())
        cases = {case["name"]: case["inputs"] for case in generate_hidden_cases(base)}
        failed = cases["revolver_maturity_no_redraw"]
        failed_outputs = value_lbo(failed)
        self.assertEqual(failed_outputs["status"], "liquidity_shortfall")
        features = exercised_features(failed, failed_outputs)
        self.assertIn("failure_with_revolver_redraw_prohibited", features)
        self.assertNotIn("mandatory_rcf_repayment", features)
        self.assertNotIn("exit_equity_bridge", features)
        funded = cases["revolver_maturity_funded"]
        funded_outputs = value_lbo(funded)
        self.assertEqual(funded_outputs["status"], "ok")
        funded_features = exercised_features(funded, funded_outputs)
        self.assertIn("mandatory_rcf_repayment", funded_features)
        self.assertNotIn("liquidity_failure", funded_features)


if __name__ == "__main__":
    unittest.main()
