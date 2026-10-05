"""Domain, branch witnesses and independence of the separate stress holdout."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from evaluator.benchmarks import BENCHMARKS
from reference.pierre_lbo.holdout import build_holdout, check_witnesses
from reference.pierre_lbo.reference import value_lbo


ROOT = Path(__file__).resolve().parents[1]


class PierreHoldoutTests(unittest.TestCase):
    def setUp(self):
        self.base = json.loads((ROOT / "tasks/pierre_lbo/inputs/base_case.json").read_text())

    def test_deterministic_nonmutating_and_independent_cases(self):
        before = deepcopy(self.base)
        cases = build_holdout(self.base)
        self.assertEqual(self.base, before)
        self.assertEqual(cases, build_holdout(self.base))
        self.assertEqual(len(cases), 22)
        self.assertEqual(len({row["name"] for row in cases}), 22)
        encoded = [json.dumps(row["inputs"], sort_keys=True) for row in cases]
        self.assertEqual(len(set(encoded)), 22)
        existing = [self.base, *[row["inputs"] for row in BENCHMARKS["pierre_lbo"].cases(self.base)],
                    *[row["inputs"] for row in json.loads((ROOT / "reference/pierre_lbo/hand_examples.json").read_text())]]
        self.assertFalse(any(row["inputs"] in existing for row in cases))
        cases[0]["inputs"]["scenarios"][0]["capex"][0] = 999.0
        self.assertEqual(cases[1]["inputs"]["scenarios"][0]["capex"][0], 0.0512)
        self.assertEqual(self.base, before)

    def test_valid_domain_and_predeclared_witnesses(self):
        for case in build_holdout(self.base):
            with self.subTest(case=case["name"]):
                before = deepcopy(case)
                output = value_lbo(case["inputs"])
                self.assertEqual(len(output), 55)
                self.assertGreater(output["entry_equity"], 0)
                self.assertTrue(check_witnesses(case, output)["passed"])
                self.assertEqual(case, before)
                json.dumps(output, allow_nan=False)

    def test_families_branches_and_currency_scaling(self):
        cases = build_holdout(self.base)
        self.assertEqual({row["family"] for row in cases}, {
            "liquidity_neighborhood", "preferred_hurdle", "mandatory_maturity",
            "revolver_no_redraw", "fiscal_dates", "dated_returns"})
        liquidity = [row for row in cases if row["family"] == "liquidity_neighborhood"]
        self.assertEqual(len(liquidity), 6)
        for factor in (0.0001, 1.0, 10000.0):
            pair = [row for row in liquidity if row["expected_features"]["currency_scale"] == factor]
            self.assertEqual({row["expected_features"]["status"] for row in pair}, {"ok", "liquidity_shortfall"})
            self.assertEqual({row["expected_features"]["guard_multiple"] for row in pair}, {0.2, 5.0})
            preferred = [row for row in cases if row["family"] == "preferred_hurdle"
                         and row["expected_features"]["currency_scale"] == factor]
            self.assertEqual({row["expected_features"]["hurdle_relation"] for row in preferred}, {"below", "equal", "above"})
            self.assertEqual(sum(not row["expected_features"]["management_irr_null"] for row in preferred), 1)
        failures = [row for row in cases if row["expected_features"]["status"] == "liquidity_shortfall"]
        self.assertEqual({row["expected_features"]["failure_period"] for row in failures}, {1, 2, 3})
        retained = next(row for row in cases if row["name"] == "holdout_revolver_repaid_then_no_redraw")
        output = value_lbo(retained["inputs"])
        self.assertEqual(output["rcf_balance"][-1], 0)
        self.assertGreater(retained["inputs"]["revolver"]["commitment"], 0)
        self.assertEqual(output["failure_period"], 3)

    def test_witnesses_reject_branch_prefix_null_and_date_changes(self):
        cases = build_holdout(self.base)
        failed = next(row for row in cases if row["expected_features"]["failure_period"] == 3)
        correct = value_lbo(failed["inputs"])
        for field, value in (("status", "ok"), ("failure_period", 2),
                             ("rcf_draw", []), ("equity_proceeds", 0.0)):
            with self.subTest(field=field):
                wrong = deepcopy(correct)
                wrong[field] = value
                self.assertFalse(check_witnesses(failed, wrong)["passed"])
        clamp = next(row for row in cases if row["name"] == "holdout_sequential_leap_clamp")
        wrong = value_lbo(clamp["inputs"])
        wrong["dates"][3] = "2028-02-29"
        self.assertFalse(check_witnesses(clamp, wrong)["passed"])


if __name__ == "__main__":
    unittest.main()
