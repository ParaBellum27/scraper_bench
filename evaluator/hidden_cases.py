"""Private scenario generation for Task 001.

Targeted cases test specific workbook relationships; seeded random cases reduce
the value of hard-coding while keeping benchmark runs reproducible.
"""
from __future__ import annotations

from copy import deepcopy
import random
from typing import Any, Dict, List


def _case(base: Dict[str, Any], name: str, overrides: Dict[str, Any]) -> Dict[str, Any]:
    inputs = deepcopy(base)
    inputs.update(overrides)
    return {"name": name, "inputs": inputs}


def targeted_cases(base: Dict[str, Any]) -> List[Dict[str, Any]]:
    scale = 2.0
    scaled = deepcopy(base)
    for key in [
        "current_ebit", "current_interest_expense", "current_capex",
        "current_depreciation", "current_revenues",
        "current_noncash_working_capital", "change_working_capital",
        "cash_and_marketable_securities", "equity_options_value",
        "book_value_debt", "prior_book_value_debt", "book_value_equity",
        "prior_book_value_equity", "shares_outstanding", "market_value_debt",
        "ebit_five_years_ago",
    ]:
        scaled[key] = float(scaled[key]) * scale

    return [
        _case(base, "discount_rate_shift", {
            "beta": 1.10,
            "riskfree_rate": 0.045,
            "risk_premium": 0.060,
            "pre_tax_cost_of_debt": 0.065,
            "stable_growth_rate": 0.04,
        }),
        _case(base, "short_high_growth_horizon", {
            "high_growth_years": 3,
            "stable_growth_rate": 0.04,
            "stable_return_on_capital": 0.10,
        }),
        _case(base, "long_high_growth_horizon", {
            "high_growth_years": 8,
            "stable_growth_rate": 0.045,
            "stable_return_on_capital": 0.11,
        }),
        _case(base, "mixed_growth_sources", {
            "ebit_five_years_ago": 3000.0,
            "outside_growth_rate": 0.09,
            "growth_weights": {"historical": 0.25, "outside": 0.35, "fundamental": 0.40},
            "stable_growth_rate": 0.04,
        }),
        _case(base, "reinvestment_and_working_capital", {
            "current_ebit": 5600.0,
            "current_capex": 2500.0,
            "current_depreciation": 1400.0,
            "current_revenues": 18000.0,
            "current_noncash_working_capital": 2500.0,
            "change_working_capital": 300.0,
            "prior_book_value_debt": 2000.0,
            "prior_book_value_equity": 16000.0,
            "stable_growth_rate": 0.04,
        }),
        _case(base, "capital_structure_shift", {
            "market_price_per_share": 75.0,
            "shares_outstanding": 800.0,
            "market_value_debt": 12000.0,
            "beta": 1.0,
            "pre_tax_cost_of_debt": 0.07,
            "stable_growth_rate": 0.04,
        }),
        _case(base, "equity_bridge_shift", {
            "cash_and_marketable_securities": 4000.0,
            "market_value_debt": 6000.0,
            "equity_options_value": 2500.0,
            "shares_outstanding": 1200.0,
            "stable_growth_rate": 0.04,
        }),
        _case(base, "interest_expense_invariance", {
            "current_interest_expense": 900.0,
        }),
        {"name": "scale_invariance_x2", "inputs": scaled},
    ]


def random_cases(base: Dict[str, Any], seed: int, count: int = 4) -> List[Dict[str, Any]]:
    rng = random.Random(seed)
    cases: List[Dict[str, Any]] = []
    for i in range(count):
        inputs = deepcopy(base)
        inputs.update({
            "current_ebit": rng.uniform(3200, 8000),
            "current_capex": rng.uniform(1300, 3200),
            "current_depreciation": rng.uniform(700, 1900),
            "tax_rate": rng.uniform(0.20, 0.34),
            "current_revenues": rng.uniform(12000, 26000),
            "current_noncash_working_capital": rng.uniform(1200, 5200),
            "change_working_capital": rng.uniform(100, 750),
            "market_price_per_share": rng.uniform(55, 170),
            "shares_outstanding": rng.uniform(650, 1400),
            "market_value_debt": rng.uniform(1000, 8500),
            "high_growth_years": rng.randint(2, 9),
            "beta": rng.uniform(0.65, 1.25),
            "riskfree_rate": rng.uniform(0.035, 0.065),
            "risk_premium": rng.uniform(0.045, 0.065),
            "pre_tax_cost_of_debt": rng.uniform(0.045, 0.08),
            "ebit_five_years_ago": rng.uniform(1000, 4200),
            "outside_growth_rate": rng.uniform(0.06, 0.15),
            "prior_book_value_debt": rng.uniform(800, 5000),
            "prior_book_value_equity": rng.uniform(8000, 24000),
            "stable_return_on_capital": rng.uniform(0.09, 0.16),
        })
        a, b, c = rng.random(), rng.random(), rng.random()
        total = a + b + c
        inputs["growth_weights"] = {
            "historical": a / total,
            "outside": b / total,
            "fundamental": c / total,
        }

        market_equity = inputs["market_price_per_share"] * inputs["shares_outstanding"]
        eq_w = market_equity / (market_equity + inputs["market_value_debt"])
        coe = inputs["riskfree_rate"] + inputs["beta"] * inputs["risk_premium"]
        at_cod = inputs["pre_tax_cost_of_debt"] * (1 - inputs["tax_rate"])
        approx_wacc = coe * eq_w + at_cod * (1 - eq_w)
        inputs["stable_growth_rate"] = min(rng.uniform(0.025, 0.05), approx_wacc - 0.015)
        if inputs["stable_growth_rate"] <= 0:
            inputs["stable_growth_rate"] = 0.02

        cases.append({"name": f"seeded_random_{i+1}", "inputs": inputs})
    return cases


def generate_hidden_cases(base: Dict[str, Any], seed: int = 20261003) -> List[Dict[str, Any]]:
    return targeted_cases(base) + random_cases(base, seed=seed, count=4)
