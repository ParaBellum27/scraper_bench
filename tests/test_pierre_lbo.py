"""Consumer-level checks with small, hand-solvable financial assumptions."""

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from evaluator.pierre_lbo_cases import generate_hidden_cases
from reference.pierre_lbo.reference import value_lbo


ROOT = Path(__file__).resolve().parents[1]
FINANCING = (
    "cash_interest", "tlb_interest", "rcf_interest", "cash_taxes",
    "pre_financing_cash_flow", "tlb_pik", "mandatory_tlb_repayment",
    "mandatory_rcf_repayment", "rcf_draw", "rcf_repayment", "tlb_sweep",
    "tlb_balance", "rcf_balance", "cash_balance",
)
EXIT = (
    "exit_ev", "exit_fees", "exit_debt", "exit_cash", "equity_value_before_floor",
    "equity_proceeds", "preferred_accrued", "preferred_payout", "ordinary_payout",
    "sponsor_proceeds", "management_proceeds", "deal_mom", "sponsor_mom",
    "management_mom", "deal_irr", "sponsor_irr", "management_irr",
)


def simple_inputs():
    # Annual EBITDA = 366. First cash year = 365 days / 366 fiscal days.
    # ACT/365 interest and holding period are exactly 1, not 365/366.
    profile = {"revenue_growth": [0.0] * 8, "gross_profit_margin": [0.5] * 8,
               "opex_margin": [0.25] * 8, "capex": [366.0] * 8}
    return {
        "case": 1, "last_fiscal_year_end": "2023-12-01", "deal_date": "2023-12-02",
        "exit_period": 1, "opening_revenue": 1464.0, "opening_working_capital": 0.0,
        "entry_multiple": 1.0, "exit_multiple": 1.0, "exit_fee_rate": 0.0,
        "tax_rate": 0.0, "ordinary_equity_fraction": 0.5,
        "management_ordinary_fraction": 0.2, "preferred_pik_rate": 0.0,
        "working_capital_ratio": [0.0] * 8,
        "term_loan": {"principal": 100.0, "cash_rate": 0.0, "pik_rate": 0.0,
                      "amortization_rate": 0.0, "cash_sweep": 0.0, "maturity_period": 20},
        "revolver": {"commitment": 1000.0, "cash_rate": 0.1, "maturity_period": 20},
        "scenarios": [deepcopy(profile) for _ in range(4)],
    }


class PierreLboTests(unittest.TestCase):
    def test_hand_solved_entry_waterfall_and_exact_schema(self):
        inputs = simple_inputs()
        before = deepcopy(inputs)
        result = value_lbo(inputs)
        self.assertEqual(inputs, before)
        expected_keys = set(FINANCING + EXIT) | {
            "status", "failure_period", "funding_shortfall", "dates", "operating_fractions",
            "interest_year_fractions", "exit_date", "holding_period_years", "entry_ebitda",
            "entry_ev", "entry_equity", "ordinary_equity", "preferred_equity",
            "sponsor_investment", "management_investment", "revenue", "gross_profit",
            "opex", "ebitda", "ebitda_margin", "working_capital", "change_working_capital",
            "cash_capex", "cash_ebitda",
        }
        self.assertEqual(set(result), expected_keys)
        self.assertEqual(result["status"], "ok")
        self.assertIsNone(result["failure_period"])
        self.assertEqual(result["dates"], ["2024-12-01"])
        for key, expected in {
            "holding_period_years": 1, "entry_ebitda": 366, "entry_ev": 366,
            "entry_equity": 266, "ordinary_equity": 133, "preferred_equity": 133,
            "management_investment": 26.6, "sponsor_investment": 239.4,
            "exit_ev": 366, "exit_debt": 100, "exit_cash": 0,
            "equity_proceeds": 266, "preferred_payout": 133, "ordinary_payout": 133,
            "management_proceeds": 26.6, "sponsor_proceeds": 239.4,
            "deal_mom": 1, "sponsor_mom": 1, "management_mom": 1,
            "deal_irr": 0, "sponsor_irr": 0, "management_irr": 0,
        }.items():
            self.assertAlmostEqual(result[key], expected, msg=key)
        self.assertEqual(result["cash_ebitda"], [365.0])
        self.assertEqual(result["cash_capex"], [365.0])
        self.assertEqual(result["interest_year_fractions"], [1.0])
        self.assertEqual(result["operating_fractions"], [365 / 366])

    def test_cash_tax_interest_and_pik_are_not_double_deducted(self):
        inputs = simple_inputs()
        inputs["scenarios"][0]["capex"] = [0.0] * 8
        inputs["term_loan"].update(cash_rate=0.1, pik_rate=0.2)
        inputs["tax_rate"] = 0.25
        result = value_lbo(inputs)
        self.assertEqual(result["tlb_interest"], [10.0])
        self.assertEqual(result["tlb_pik"], [20.0])
        self.assertEqual(result["cash_taxes"], [88.75])
        self.assertEqual(result["pre_financing_cash_flow"], [276.25])
        self.assertEqual(result["cash_balance"], [266.25])
        self.assertEqual(result["tlb_balance"], [120.0])

    def test_working_capital_is_not_stubbed(self):
        inputs = simple_inputs()
        inputs["deal_date"] = "2024-11-30"
        inputs["opening_working_capital"] = 10.0
        inputs["working_capital_ratio"] = [0.25] * 8
        inputs["scenarios"][0]["capex"] = [0.0] * 8
        result = value_lbo(inputs)
        self.assertEqual(result["cash_ebitda"], [1.0])
        self.assertEqual(result["working_capital"], [366.0])
        self.assertEqual(result["change_working_capital"], [356.0])
        self.assertEqual(result["rcf_draw"], [355.0])
        self.assertEqual(result["rcf_interest"], [0.0])
        self.assertEqual(result["entry_ebitda"], 366.0)

    def test_revolver_repays_before_sweep_and_uses_opening_interest(self):
        inputs = simple_inputs()
        inputs["exit_period"] = 2
        inputs["scenarios"][0]["capex"][0:2] = [466.0, 0.0]
        inputs["term_loan"]["cash_sweep"] = 1.0
        result = value_lbo(inputs)
        drawn = 100 * 365 / 366
        self.assertAlmostEqual(result["rcf_draw"][0], drawn)
        self.assertEqual(result["rcf_interest"][0], 0)
        self.assertAlmostEqual(result["rcf_interest"][1], drawn * 0.1)
        self.assertAlmostEqual(result["rcf_repayment"][1], drawn)
        self.assertEqual(result["tlb_sweep"], [0.0, 100.0])
        self.assertEqual(result["tlb_balance"], [100.0, 0.0])
        self.assertEqual(result["rcf_balance"][1], 0)
        self.assertAlmostEqual(result["cash_balance"][1], 366 - drawn * 1.1 - 100)

    def test_shortfall_has_no_fabricated_failed_financing_row(self):
        inputs = simple_inputs()
        inputs["exit_period"] = 3
        inputs["scenarios"][0]["capex"][1] = 500.0
        inputs["revolver"]["commitment"] = 10.0
        result = value_lbo(inputs)
        self.assertEqual(result["status"], "liquidity_shortfall")
        self.assertEqual(result["failure_period"], 2)
        self.assertEqual(result["funding_shortfall"], 124.0)
        for key in FINANCING:
            self.assertEqual(len(result[key]), 1, key)
        for key in EXIT:
            self.assertIsNone(result[key], key)
        self.assertEqual(len(result["ebitda"]), 3)
        self.assertEqual(len(result["dates"]), 3)
        self.assertEqual(result["exit_date"], "2026-12-01")
        self.assertEqual(result["entry_equity"], 266)
        inputs["scenarios"][0]["capex"][0] = 1000.0
        first = value_lbo(inputs)
        self.assertEqual(first["failure_period"], 1)
        for key in FINANCING:
            self.assertEqual(first[key], [])

    def test_maturity_pays_pik_and_can_refinance_with_revolver(self):
        inputs = simple_inputs()
        inputs["term_loan"].update(maturity_period=1, pik_rate=0.2)
        result = value_lbo(inputs)
        self.assertEqual(result["mandatory_tlb_repayment"], [120.0])
        self.assertEqual(result["tlb_balance"], [0.0])
        self.assertEqual(result["rcf_draw"], [120.0])
        inputs["revolver"]["maturity_period"] = 1
        failed = value_lbo(inputs)
        self.assertEqual(failed["funding_shortfall"], 120.0)
        self.assertEqual(failed["failure_period"], 1)

    def test_revolver_maturity_is_total_repayment_not_reborrowing(self):
        inputs = simple_inputs()
        inputs["exit_period"] = 2
        inputs["scenarios"][0]["capex"][0] = 466.0
        inputs["revolver"]["maturity_period"] = 2
        failed = value_lbo(inputs)
        self.assertEqual(failed["failure_period"], 2)
        inputs["scenarios"][0]["capex"][1] = 0.0
        result = value_lbo(inputs)
        drawn = 100 * 365 / 366
        self.assertAlmostEqual(result["mandatory_rcf_repayment"][1], drawn)
        self.assertAlmostEqual(result["rcf_repayment"][1], drawn)
        self.assertEqual(result["rcf_draw"][1], 0)
        self.assertEqual(result["rcf_balance"][1], 0)

    def test_scheduled_amortization_and_sweep_cannot_overpay(self):
        inputs = simple_inputs()
        inputs["exit_period"] = 3
        inputs["scenarios"][0]["capex"] = [0.0] * 8
        inputs["term_loan"].update(amortization_rate=0.8, cash_sweep=1.0, pik_rate=0.02)
        result = value_lbo(inputs)
        amortization = 80 * 365 / 366
        self.assertAlmostEqual(result["mandatory_tlb_repayment"][0], amortization)
        self.assertAlmostEqual(result["tlb_sweep"][0], 102 - amortization)
        self.assertEqual(result["tlb_balance"], [0.0, 0.0, 0.0])
        self.assertEqual(result["mandatory_tlb_repayment"][1:], [0.0, 0.0])
        self.assertEqual(result["tlb_pik"], [2.0, 0.0, 0.0])
        self.assertAlmostEqual(result["cash_balance"][0], 263)
        inputs["term_loan"].update(cash_sweep=0, pik_rate=0)
        result = value_lbo(inputs)
        self.assertAlmostEqual(result["mandatory_tlb_repayment"][1], 100 - amortization)
        self.assertEqual(result["mandatory_tlb_repayment"][2], 0)

    def test_preferred_boundary_and_actual_date_accretion(self):
        for proceeds, preferred, ordinary in ((132, 132, 0), (133, 133, 0), (134, 133, 1)):
            inputs = simple_inputs()
            inputs["exit_multiple"] = (proceeds + 100) / 366
            result = value_lbo(inputs)
            self.assertAlmostEqual(result["preferred_payout"], preferred)
            self.assertAlmostEqual(result["ordinary_payout"], ordinary)
            self.assertAlmostEqual(result["management_proceeds"], ordinary * 0.2)
            self.assertAlmostEqual(result["management_proceeds"] + result["sponsor_proceeds"], proceeds)
            if ordinary == 0:
                self.assertIsNone(result["management_irr"])
        inputs = simple_inputs()
        inputs["exit_period"] = 2
        inputs["preferred_pik_rate"] = 0.1
        result = value_lbo(inputs)
        self.assertEqual(result["holding_period_years"], 2)
        self.assertAlmostEqual(result["preferred_accrued"], 133 * 1.21)
        self.assertAlmostEqual(result["management_irr"], (105.07 / 133) ** 0.5 - 1)

    def test_zero_investments_and_zero_payout_have_null_irrs(self):
        inputs = simple_inputs()
        inputs["management_ordinary_fraction"] = 0
        result = value_lbo(inputs)
        self.assertIsNone(result["management_mom"])
        self.assertIsNone(result["management_irr"])
        inputs.update(ordinary_equity_fraction=1, management_ordinary_fraction=1)
        result = value_lbo(inputs)
        self.assertEqual(result["preferred_payout"], 0)
        self.assertIsNone(result["sponsor_mom"])
        self.assertIsNone(result["sponsor_irr"])
        inputs = simple_inputs()
        inputs["exit_multiple"] = 0
        result = value_lbo(inputs)
        self.assertEqual(result["equity_value_before_floor"], -100)
        for owner in ("deal", "sponsor", "management"):
            self.assertEqual(result[owner + "_mom"], 0)
            self.assertIsNone(result[owner + "_irr"])

    def test_negative_ebitda_has_no_tax_refund_or_negative_exit_fee(self):
        inputs = simple_inputs()
        inputs["exit_period"] = 2
        inputs["scenarios"][0]["opex_margin"][1] = 0.75
        inputs["tax_rate"] = 0.25
        inputs["exit_fee_rate"] = 0.1
        result = value_lbo(inputs)
        self.assertEqual(result["ebitda"][1], -366)
        self.assertEqual(result["cash_taxes"][1], 0)
        self.assertEqual(result["exit_ev"], -366)
        self.assertEqual(result["exit_fees"], 0)
        self.assertEqual(result["equity_proceeds"], 0)

    def test_sequential_leap_clamp_and_noninteger_actual_date_return(self):
        inputs = simple_inputs()
        inputs.update(last_fiscal_year_end="2020-02-29", deal_date="2020-03-01", exit_period=5)
        inputs["scenarios"][0]["capex"] = [0.0] * 8
        inputs["term_loan"]["cash_rate"] = 0.1
        result = value_lbo(inputs)
        self.assertEqual(result["dates"], ["2021-02-28", "2022-02-28", "2023-02-28", "2024-02-28", "2025-02-28"])
        self.assertEqual(result["operating_fractions"], [364 / 365, 1, 1, 1, 1])
        self.assertEqual(result["interest_year_fractions"], [364 / 365, 1, 1, 1, 366 / 365])
        self.assertAlmostEqual(result["tlb_interest"][-1], 10 * 366 / 365)
        inputs = simple_inputs()
        inputs.update(deal_date="2024-02-29", exit_multiple=2)
        result = value_lbo(inputs)
        self.assertEqual(result["holding_period_years"], 276 / 365)
        self.assertAlmostEqual(result["deal_mom"], 632 / 266)
        self.assertAlmostEqual(result["deal_irr"], (632 / 266) ** (365 / 276) - 1)

    def test_profiles_growth_and_closing_working_capital_roll_forward(self):
        inputs = simple_inputs()
        inputs.update(case=4, exit_period=2, opening_working_capital=10)
        inputs["scenarios"][3]["revenue_growth"][0:2] = [0.5, -0.5]
        inputs["working_capital_ratio"][0:2] = [0.1, 0.2]
        result = value_lbo(inputs)
        self.assertEqual(result["revenue"], [2196, 1098])
        self.assertAlmostEqual(result["change_working_capital"][0], 209.6)
        self.assertAlmostEqual(result["change_working_capital"][1], 0)
        self.assertEqual(result["entry_ebitda"], 549)
        self.assertEqual(result["ebitda"][-1], 274.5)

    def test_invalid_domains_are_value_errors(self):
        invalid = [
            ("case", True), ("case", 0), ("exit_period", 1.0), ("exit_period", 9),
            ("opening_revenue", 0), ("opening_revenue", float("nan")),
            ("opening_working_capital", -1), ("entry_multiple", 0),
            ("exit_multiple", -1), ("tax_rate", 1.1), ("exit_fee_rate", False),
            ("ordinary_equity_fraction", -0.1), ("management_ordinary_fraction", 1.1),
            ("preferred_pik_rate", float("inf")), ("working_capital_ratio", [0] * 7),
            ("deal_date", "2023-12-01"), ("deal_date", "2024-12-01"),
            ("deal_date", "2024-02-30"), ("deal_date", "20240229"),
            ("last_fiscal_year_end", None), ("scenarios", []),
        ]
        for key, value in invalid:
            with self.subTest(key=key, value=value):
                inputs = simple_inputs()
                inputs[key] = value
                with self.assertRaises(ValueError):
                    value_lbo(inputs)
        for group, key, value in (
            ("term_loan", "principal", -1), ("term_loan", "cash_rate", True),
            ("term_loan", "pik_rate", -0.1), ("term_loan", "amortization_rate", 1.1),
            ("term_loan", "cash_sweep", -0.1), ("term_loan", "maturity_period", 0),
            ("revolver", "commitment", -1), ("revolver", "cash_rate", float("nan")),
            ("revolver", "maturity_period", 2.0),
        ):
            with self.subTest(group=group, key=key):
                inputs = simple_inputs()
                inputs[group][key] = value
                with self.assertRaises(ValueError):
                    value_lbo(inputs)
        for key, value in (("revenue_growth", -1), ("gross_profit_margin", 1.1),
                           ("opex_margin", -0.1), ("capex", -1)):
            inputs = simple_inputs()
            inputs["scenarios"][3][key][7] = value  # Validate even unselected profiles.
            with self.assertRaises(ValueError):
                value_lbo(inputs)
        for value in (None, [], {}, {**simple_inputs(), "extra": 1}):
            with self.assertRaises(ValueError):
                value_lbo(json.loads(json.dumps(value)))

    def test_scaled_inputs_have_hand_solved_scaled_value(self):
        inputs = simple_inputs()
        inputs["opening_revenue"] *= 1000
        inputs["term_loan"]["principal"] *= 1000
        inputs["revolver"]["commitment"] *= 1000
        for profile in inputs["scenarios"]:
            profile["capex"] = [366000.0] * 8
        result = value_lbo(inputs)
        self.assertEqual(result["entry_equity"], 266000)
        self.assertEqual(result["equity_proceeds"], 266000)
        self.assertEqual(result["deal_mom"], 1)
        self.assertEqual(result["deal_irr"], 0)

    def test_generator_is_pure_deterministic_and_has_distinct_finance_cases(self):
        base = json.loads((ROOT / "tasks/pierre_lbo/inputs/base_case.json").read_text())
        before = deepcopy(base)
        cases = generate_hidden_cases(base)
        self.assertEqual(base, before)
        self.assertEqual(cases, generate_hidden_cases(base))
        self.assertNotEqual(cases, generate_hidden_cases(base, seed=7))
        cases[0]["inputs"]["scenarios"][0]["capex"][0] = -999
        self.assertEqual(base, before)
        self.assertNotEqual(cases[1]["inputs"]["scenarios"][0]["capex"][0], -999)

    def test_standalone_copy_runs_json_protocol_outside_repository(self):
        source = ROOT / "reference/pierre_lbo/reference.py"
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / "solution.py"
            script.write_bytes(source.read_bytes())
            process = subprocess.run([sys.executable, "-I", str(script)],
                                     input=json.dumps(simple_inputs()), text=True,
                                     capture_output=True, cwd=directory, timeout=10)
        self.assertEqual(process.returncode, 0, process.stderr)
        result = json.loads(process.stdout)
        self.assertEqual(result["equity_proceeds"], 266)
        self.assertEqual(result["status"], "ok")


if __name__ == "__main__":
    unittest.main()
