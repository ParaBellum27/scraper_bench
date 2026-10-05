"""Task 001 input/output field definitions."""
from __future__ import annotations

from typing import Any, Dict

REQUIRED_OUTPUT_FIELDS = {
    "cost_of_equity",
    "equity_weight",
    "after_tax_cost_of_debt",
    "debt_weight",
    "wacc",
    "current_fcff",
    "historical_growth_rate",
    "fundamental_roc",
    "fundamental_reinvestment_rate",
    "fundamental_growth_rate",
    "weighted_growth_rate",
    "working_capital_pct_revenue",
    "high_growth_fcff",
    "high_growth_pv",
    "stable_reinvestment_rate",
    "terminal_fcff",
    "stable_wacc",
    "terminal_value",
    "pv_high_growth_fcff",
    "pv_terminal_value",
    "firm_value",
    "market_value_equity",
    "equity_value_per_share",
}


def validate_submission_output(output: Dict[str, Any]) -> None:
    if not isinstance(output, dict):
        raise TypeError("submission output must be a JSON object")
    missing = REQUIRED_OUTPUT_FIELDS - set(output)
    if missing:
        raise ValueError(f"missing required output fields: {sorted(missing)}")
