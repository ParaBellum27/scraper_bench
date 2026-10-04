"""Scoring logic for Task 001: Damodaran two-stage FCFF coding benchmark."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from math import isclose, isfinite
from typing import Any, Dict, Iterable, List, Tuple

REL_TOL = 1e-5
ABS_TOL = 1e-6

SCORING_GROUPS = {
    "discount_rate": (0.15, [
        "cost_of_equity", "equity_weight", "after_tax_cost_of_debt", "debt_weight", "wacc"
    ]),
    "growth_reinvestment": (0.15, [
        "historical_growth_rate", "fundamental_roc", "fundamental_reinvestment_rate",
        "fundamental_growth_rate", "weighted_growth_rate", "working_capital_pct_revenue"
    ]),
    "high_growth_fcff": (0.25, [
        "current_fcff", "high_growth_fcff", "high_growth_pv"
    ]),
    "terminal_value": (0.20, [
        "stable_reinvestment_rate", "terminal_fcff", "stable_wacc", "terminal_value"
    ]),
    "valuation_bridge": (0.25, [
        "pv_high_growth_fcff", "pv_terminal_value", "firm_value",
        "market_value_equity", "equity_value_per_share"
    ]),
}


@dataclass
class CaseResult:
    name: str
    score: float
    group_scores: Dict[str, float]
    missing_fields: List[str]
    mismatches: Dict[str, Any]
    execution_error: str | None = None


def _numeric_ok(actual: Any, expected: float) -> bool:
    if isinstance(actual, bool) or not isinstance(actual, (int, float)):
        return False
    a = float(actual)
    return isfinite(a) and isclose(a, float(expected), rel_tol=REL_TOL, abs_tol=ABS_TOL)


def _field_fraction(actual: Any, expected: Any) -> Tuple[float, Any | None]:
    if isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            return 0.0, {
                "expected_length": len(expected),
                "actual_length": len(actual) if isinstance(actual, list) else None,
            }
        oks = [_numeric_ok(a, e) for a, e in zip(actual, expected)]
        bad = [i for i, ok in enumerate(oks) if not ok]
        return (sum(oks) / len(oks) if oks else 1.0), ({"bad_indices": bad} if bad else None)
    ok = _numeric_ok(actual, expected)
    if ok:
        return 1.0, None
    return 0.0, {"expected": expected, "actual": actual}


def grade_case(name: str, actual: Dict[str, Any] | None, expected: Dict[str, Any], execution_error: str | None = None) -> CaseResult:
    if execution_error is not None or not isinstance(actual, dict):
        return CaseResult(
            name=name,
            score=0.0,
            group_scores={},
            missing_fields=[],
            mismatches={},
            execution_error=execution_error or "submission did not return a JSON object",
        )

    group_scores: Dict[str, float] = {}
    missing: List[str] = []
    mismatches: Dict[str, Any] = {}
    total = 0.0

    for group, (weight, fields) in SCORING_GROUPS.items():
        field_scores = []
        for field in fields:
            if field not in actual:
                missing.append(field)
                field_scores.append(0.0)
                continue
            fraction, mismatch = _field_fraction(actual[field], expected[field])
            field_scores.append(fraction)
            if mismatch is not None:
                mismatches[field] = mismatch
        group_score = sum(field_scores) / len(field_scores)
        group_scores[group] = group_score
        total += weight * group_score

    return CaseResult(
        name=name,
        score=100.0 * total,
        group_scores=group_scores,
        missing_fields=sorted(set(missing)),
        mismatches=mismatches,
    )


def summarize(base_result: CaseResult, hidden_results: Iterable[CaseResult]) -> Dict[str, Any]:
    hidden = list(hidden_results)
    hidden_avg = sum(x.score for x in hidden) / len(hidden) if hidden else 0.0
    final_score = 0.20 * base_result.score + 0.80 * hidden_avg
    return {
        "score": final_score,
        "base_case_score": base_result.score,
        "hidden_average_score": hidden_avg,
        "hidden_cases_passed_95": sum(r.score >= 95.0 for r in hidden),
        "hidden_cases_total": len(hidden),
        "base_case": asdict(base_result),
        "hidden_cases": [asdict(r) for r in hidden],
    }
