"""Task selection for the shared isolated grading runner."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from evaluator.grader import ABS_TOL, REL_TOL, SCORING_GROUPS
from evaluator.hidden_cases import generate_hidden_cases as fcff_cases
from evaluator.pierre_lbo_cases import generate_hidden_cases as lbo_cases
from reference.damodaran_fcff2st.reference import value_company
from reference.pierre_lbo.reference import value_lbo


LBO_SCORING_GROUPS = {
    "status_and_timing": (0.05, [
        "status", "failure_period", "funding_shortfall", "dates",
        "operating_fractions", "interest_year_fractions", "exit_date", "holding_period_years",
    ]),
    "entry_funding": (0.10, [
        "entry_ebitda", "entry_ev", "entry_equity", "ordinary_equity",
        "preferred_equity", "sponsor_investment", "management_investment",
    ]),
    "operating_forecast": (0.25, [
        "revenue", "gross_profit", "opex", "ebitda", "ebitda_margin",
        "working_capital", "change_working_capital", "cash_capex", "cash_ebitda",
    ]),
    "debt_and_cash": (0.30, [
        "cash_interest", "tlb_interest", "rcf_interest", "cash_taxes",
        "pre_financing_cash_flow", "tlb_pik", "mandatory_tlb_repayment",
        "mandatory_rcf_repayment", "rcf_draw", "rcf_repayment", "tlb_sweep",
        "tlb_balance", "rcf_balance", "cash_balance",
    ]),
    "exit_bridge": (0.15, [
        "exit_ev", "exit_fees", "exit_debt", "exit_cash",
        "equity_value_before_floor", "equity_proceeds",
    ]),
    "waterfall_and_returns": (0.15, [
        "preferred_accrued", "preferred_payout", "ordinary_payout",
        "sponsor_proceeds", "management_proceeds", "deal_mom", "sponsor_mom",
        "management_mom", "deal_irr", "sponsor_irr", "management_irr",
    ]),
}


@dataclass(frozen=True)
class Benchmark:
    reference: Callable[[dict[str, Any]], dict[str, Any]]
    cases: Callable[..., list[dict[str, Any]]]
    scoring_groups: dict[str, tuple[float, list[str]]]
    seed: int
    rel_tol: float
    abs_tol: float

    def base_input(self, root: Path, name: str) -> Path:
        return root / "tasks" / name / "inputs" / "base_case.json"


BENCHMARKS = {
    "damodaran_fcff2st": Benchmark(value_company, fcff_cases, SCORING_GROUPS, 20261003, REL_TOL, ABS_TOL),
    "pierre_lbo": Benchmark(value_lbo, lbo_cases, LBO_SCORING_GROUPS, 20261004, 1e-7, 1e-7),
}
