"""Predeclared, separate Pierre LBO stress holdout; never an official scoreboard.

All inputs and witnesses are constructed before any submission is read. Qualification
requires every recalculated workbook's complete 55-field output and independent
witnesses to agree. Candidate execution is gated on the entire qualification.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from dataclasses import asdict
from datetime import date, datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import subprocess

from evaluator.benchmarks import BENCHMARKS
from evaluator.grader import grade_case
from evaluator.run_grader import run_submission
from reference.pierre_lbo.qualify import _convert_with_libreoffice
from reference.pierre_lbo.reference import EXIT_FIELDS, FINANCING_FIELDS
from reference.pierre_lbo.workbook import build_workbook, read_workbook_outputs


def _simple(base: dict) -> dict:
    value = deepcopy(base)
    value.update(case=1, last_fiscal_year_end="2026-06-30", deal_date="2026-07-01",
                 exit_period=1, opening_revenue=2048.0, opening_working_capital=0.0,
                 entry_multiple=2.0, exit_multiple=2.0, exit_fee_rate=0.0,
                 tax_rate=0.0, ordinary_equity_fraction=0.5,
                 management_ordinary_fraction=0.3, preferred_pik_rate=0.0,
                 working_capital_ratio=[0.0] * 8)
    value["term_loan"] = dict(principal=128.0, cash_rate=0.0, pik_rate=0.0,
                              amortization_rate=0.0, cash_sweep=0.0, maturity_period=12)
    value["revolver"] = dict(commitment=192.0, cash_rate=0.0, maturity_period=12)
    profile = dict(revenue_growth=[0.0] * 8, gross_profit_margin=[0.375] * 8,
                   opex_margin=[0.125] * 8, capex=[512.0] * 8)
    value["scenarios"] = [deepcopy(profile) for _ in range(4)]
    return value


def _scale(inputs: dict, factor: float) -> None:
    for field in ("opening_revenue", "opening_working_capital"):
        inputs[field] *= factor
    inputs["term_loan"]["principal"] *= factor
    inputs["revolver"]["commitment"] *= factor
    for profile in inputs["scenarios"]:
        profile["capex"] = [amount * factor for amount in profile["capex"]]


def build_holdout(base: dict) -> list[dict]:
    """Return 22 independent, deterministic cases without evaluating any oracle.

    Hand setup: annual EBITDA512, entry equity896, preferred448. Neutral
    capex512 cancels cash EBITDA even in stubs. First owned fraction364/365.
    Liquidity shortages are 0.2 or 5 times the operand-relative guard, not ULPs.
    """
    cases = []

    def add(name, family, inputs, failure=None, **features):
        horizon = inputs["exit_period"]
        witnesses = dict(status="ok" if failure is None else "liquidity_shortfall",
                         failure_period=failure,
                         financing_prefix_length=horizon if failure is None else failure - 1,
                         planned_periods=horizon, exit_fields_null=failure is not None)
        witnesses.update(features)
        cases.append(dict(name=name, family=family, inputs=inputs, expected_features=witnesses))

    for label, factor in (("small", 0.0001), ("unit", 1.0), ("large", 10000.0)):
        for side, guard_multiple in (("inside", 0.2), ("outside", 5.0)):
            value = _simple(base)
            value["revolver"]["commitment"] = 32.0
            guard = 512.0 * 364 / 365 * 1e-12
            value["working_capital_ratio"] = [(32.0 + guard_multiple * guard) / 2048.0] * 8
            _scale(value, factor)
            add(f"holdout_liquidity_{side}_{label}", "liquidity_neighborhood", value,
                failure=1 if side == "outside" else None,
                currency_scale=factor, guard_multiple=guard_multiple,
                arithmetic="Neutral stub EBITDA/capex; full WC consumes commitment plus specified guard multiple.")
        for side, delta in (("below", -2.0), ("equal", 0.0), ("above", 2.0)):
            value = _simple(base)
            value["exit_multiple"] = (128.0 + 448.0 + delta) / 512.0
            _scale(value, factor)
            add(f"holdout_preferred_{side}_{label}", "preferred_hurdle", value,
                currency_scale=factor, hurdle_relation=side,
                ordinary_payout_zero=side != "above", management_irr_null=side != "above",
                expected_subset={"equity_proceeds": (448.0 + delta) * factor,
                                 "preferred_accrued": 448.0 * factor,
                                 "ordinary_payout": max(delta, 0) * factor},
                arithmetic="Entry equity896, preferred448; neutral operations leave debt128 and no cash.")

    value = _simple(base)
    value["exit_period"] = 3
    value["term_loan"]["maturity_period"] = 2
    add("holdout_term_maturity_funded", "mandatory_maturity", value,
        expected_subset={"mandatory_tlb_repayment": [0.0, 128.0, 0.0],
                         "rcf_draw": [0.0, 128.0, 0.0]},
        arithmetic="Neutral operations; period2 refinances all original debt128 into revolver192.")
    value = _simple(base)
    value["exit_period"] = 4
    value["term_loan"]["maturity_period"] = 3
    value["revolver"]["commitment"] = 64.0
    add("holdout_term_maturity_retained_prefix", "mandatory_maturity", value, failure=3,
        expected_subset={"funding_shortfall": 64.0, "tlb_balance": [128.0, 128.0]},
        arithmetic="Two neutral rows survive; mandatory128 exceeds available64 in period3.")
    value = _simple(base)
    value["exit_period"] = 3
    value["revolver"]["maturity_period"] = 2
    value["scenarios"][0]["capex"][0] = 640.0
    first_draw = 128.0 * 364 / 365
    add("holdout_revolver_no_redraw_failure", "revolver_no_redraw", value, failure=2,
        expected_subset={"rcf_draw": [first_draw], "funding_shortfall": first_draw},
        arithmetic="First deficit128*364/365 is borrowed; neutral second row cannot repay matured revolver.")
    value = deepcopy(value)
    value["exit_period"] = 4
    value["scenarios"][0]["capex"][1:3] = [0.0, 1100.0]
    add("holdout_revolver_repaid_then_no_redraw", "revolver_no_redraw", value, failure=3,
        expected_subset={"mandatory_rcf_repayment": [0.0, first_draw],
                         "rcf_draw": [first_draw, 0.0], "rcf_balance": [first_draw, 0.0],
                         "funding_shortfall": 588.0 - (512.0 - first_draw)},
        arithmetic="Period2 retains512-first_draw after maturity repayment; period3 deficit588 cannot redraw unused commitment.")

    value = _simple(base)
    value.update(last_fiscal_year_end="2024-02-29", deal_date="2024-10-15", exit_period=5)
    dates = [f"{year}-02-28" for year in range(2025, 2030)]
    add("holdout_sequential_leap_clamp", "fiscal_dates", value, dates=dates,
        expected_subset={"operating_fractions": [136 / 365, 1.0, 1.0, 1.0, 1.0],
                         "holding_period_years": (date(2029, 2, 28) - date(2024, 10, 15)).days / 365},
        arithmetic="EDATE sequentially clamps Feb29 to Feb28; later leap2028 must remain Feb28.")
    value = _simple(base)
    value.update(last_fiscal_year_end="2027-06-30", deal_date="2028-06-29", exit_multiple=2.25)
    value["working_capital_ratio"] = [0.0625] * 8
    add("holdout_one_day_stub_full_working_capital", "fiscal_dates", value,
        dates=["2028-06-30"], expected_subset={"operating_fractions": [1 / 366],
        "interest_year_fractions": [1 / 365], "change_working_capital": [128.0],
        "rcf_draw": [128.0]}, arithmetic="One owned day in leap fiscal year; full WC128 is not stubbed.")
    value = _simple(base)
    value.update(last_fiscal_year_end="2031-09-30", deal_date="2032-02-29", exit_multiple=3.0)
    years = 214 / 365
    add("holdout_leap_close_dated_returns", "dated_returns", value, dates=["2032-09-30"],
        expected_subset={"holding_period_years": years, "deal_mom": 1408 / 896,
                         "management_mom": 960 / 448,
                         "deal_irr": (1408 / 896) ** (1 / years) - 1,
                         "management_irr": (960 / 448) ** (1 / years) - 1},
        arithmetic="214 actual owned days; EV1536 less debt128 gives1408; preferred448 leaves ordinary960.")
    return cases


def check_witnesses(case: dict, output: dict) -> dict:
    """Cross-check predeclared branch, prefix, null and arithmetic expectations."""
    features = case["expected_features"]
    failures = []
    for field in ("status", "failure_period"):
        if output.get(field) != features[field]:
            failures.append(field)
    for field in FINANCING_FIELDS:
        if not isinstance(output.get(field), list) or len(output[field]) != features["financing_prefix_length"]:
            failures.append(field + ".prefix")
    for field in ("dates", "revenue", "cash_ebitda"):
        if not isinstance(output.get(field), list) or len(output[field]) != features["planned_periods"]:
            failures.append(field + ".planned")
    if features["exit_fields_null"] and any(output.get(field) is not None for field in EXIT_FIELDS):
        failures.append("exit_fields_null")
    if not features["exit_fields_null"] and output.get("equity_proceeds") is None:
        failures.append("financed_exit")
    for feature, field in (("ordinary_payout_zero", "ordinary_payout"), ("management_irr_null", "management_irr")):
        if feature in features:
            observed = output.get(field) == 0 if feature.endswith("zero") else output.get(field) is None
            if observed != features[feature]:
                failures.append(feature)
    if "dates" in features and output.get("dates") != features["dates"]:
        failures.append("dates")
    subset = features.get("expected_subset", {})
    grade = grade_case(case["name"], output, subset,
                       scoring_groups={"predeclared_arithmetic": (1.0, list(subset))},
                       rel_tol=1e-9, abs_tol=1e-12) if subset else None
    if grade and (grade.missing_fields or grade.mismatches):
        failures.append("predeclared_arithmetic")
    return dict(passed=not failures, failures=failures, arithmetic_grade=asdict(grade) if grade else None)


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _save(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    benchmark = BENCHMARKS["pierre_lbo"]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--soffice", type=Path, required=True)
    parser.add_argument("--submission", type=Path)
    parser.add_argument("--timeout", type=float, default=5.0)
    args = parser.parse_args()
    if not args.soffice.is_absolute() or not args.soffice.is_file():
        parser.error("--soffice must be an absolute executable file path")
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("--timeout must be positive and finite")
    base_path = benchmark.base_input(root, "pierre_lbo")
    cases = build_holdout(json.loads(base_path.read_text()))
    forbidden = [json.loads(base_path.read_text()), *[row["inputs"] for row in benchmark.cases(json.loads(base_path.read_text()), seed=benchmark.seed)],
                 *[row["inputs"] for row in json.loads((root / "reference/pierre_lbo/hand_examples.json").read_text())]]
    if len(cases) != 22 or len({row["name"] for row in cases}) != len(cases):
        raise ValueError("Holdout requires exactly22 distinct case names")
    if any(row["inputs"] in forbidden for row in cases):
        raise ValueError("Holdout duplicates existing scored or hand inputs")
    args.output_dir.mkdir(parents=True, exist_ok=False)
    _save(args.output_dir / "cases.json", cases)
    sources = ("reference/pierre_lbo/holdout.py", "reference/pierre_lbo/reference.py",
               "reference/pierre_lbo/workbook.py", "reference/pierre_lbo/qualify.py",
               "evaluator/benchmarks.py", "evaluator/grader.py", "evaluator/run_grader.py",
               "evaluator/pierre_lbo_cases.py", "harness/executor.py", "tasks/pierre_lbo/task.md",
               "reference/pierre_lbo/hand_examples.json")
    hashes = {name: _hash(root / name) for name in sources}
    snapshot = args.output_dir / "sources"
    for name in sources:
        target = snapshot / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((root / name).read_bytes())
    required = {field for _, fields in benchmark.scoring_groups.values() for field in fields}
    if len(required) != 55:
        raise ValueError("Expected unchanged55-field benchmark")
    report: dict = dict(benchmark="pierre_lbo", suite="fresh_holdout", official_scoreboard=False,
                  created_at=datetime.now(timezone.utc).isoformat(), engine="libreoffice",
                  qualified=False, base_input_sha256=_hash(base_path),
                  cases_sha256=_hash(args.output_dir / "cases.json"), source_sha256_before=hashes,
                  rel_tol=benchmark.rel_tol, abs_tol=benchmark.abs_tol,
                  cases_total=len(cases), cases_passed=0, cases=[], submission=None)
    _save(args.output_dir / "report.json", report)
    try:
        report["engine_version"] = subprocess.run([str(args.soffice), "--version"],
            capture_output=True, text=True, check=True, timeout=30).stdout.strip()
        for case in cases:
            row = dict(case, passed=False, fields_compared=55)
            report["cases"].append(row)
            try:
                expected = benchmark.reference(case["inputs"])
                row["expected"] = expected
                if set(expected) != required:
                    raise ValueError("Reference violates55-field contract")
                row["reference_witnesses"] = check_witnesses(case, expected)
                raw = args.output_dir / (case["name"] + ".xlsx")
                build_workbook(case["inputs"], raw)
                row.update(workbook_source=str(raw), workbook_source_sha256=_hash(raw))
                calculated = _convert_with_libreoffice(raw, str(args.soffice))
                row.update(workbook=str(calculated), workbook_sha256=_hash(calculated))
                actual = read_workbook_outputs(calculated)
                row["spreadsheet"] = actual
                row["spreadsheet_witnesses"] = check_witnesses(case, actual)
                grade = grade_case(case["name"], actual, expected, scoring_groups=benchmark.scoring_groups,
                                   rel_tol=benchmark.rel_tol, abs_tol=benchmark.abs_tol)
                row["grade"] = asdict(grade)
                row["passed"] = (set(actual) == required and not grade.missing_fields and not grade.mismatches
                                 and row["reference_witnesses"]["passed"] and row["spreadsheet_witnesses"]["passed"])
            except Exception as error:
                row["error"] = f"{type(error).__name__}: {error}"
            report["cases_passed"] = sum(item["passed"] for item in report["cases"])
            _save(args.output_dir / "report.json", report)
        report["source_sha256_after"] = {name: _hash(root / name) for name in sources}
        report["sources_unchanged"] = report["source_sha256_after"] == hashes
        report["qualified"] = report["cases_passed"] == len(cases) and report["sources_unchanged"]
        if args.submission and report["qualified"]:
            # Read/copy the frozen program only after ALL expected workbooks qualify.
            before = _hash(args.submission)
            frozen = args.output_dir / "frozen_submission.py"
            frozen.write_bytes(args.submission.read_bytes())
            if _hash(frozen) != before:
                raise RuntimeError("Submission changed while being frozen")
            result: dict = dict(primary_metric="holdout_cases_fully_correct", score_role="weighted_partial_credit_diagnostic",
                          submission_sha256_before=before, grading_timeout_seconds=args.timeout,
                          cases_total=len(cases), cases_fully_correct=0, all_cases_correct=False, cases=[])
            report["submission"] = result
            for case, qualified in zip(cases, report["cases"]):
                actual, error = run_submission(frozen.resolve(), case["inputs"], args.timeout)
                grade = grade_case(case["name"], actual, qualified["expected"], error,
                                   scoring_groups=benchmark.scoring_groups, rel_tol=benchmark.rel_tol, abs_tol=benchmark.abs_tol)
                passed = grade.execution_error is None and not grade.missing_fields and not grade.mismatches
                result["cases"].append(dict(name=case["name"], actual=actual, grade=asdict(grade), fully_correct=passed))
                _save(args.output_dir / "report.json", report)
            result["submission_sha256_after"] = _hash(args.submission)
            result["frozen_submission_sha256_after"] = _hash(frozen)
            result["source_unchanged"] = before == result["submission_sha256_after"] == result["frozen_submission_sha256_after"]
            result["cases_fully_correct"] = sum(row["fully_correct"] for row in result["cases"])
            result["all_cases_correct"] = result["source_unchanged"] and result["cases_fully_correct"] == len(cases)
            result["score"] = sum(row["grade"]["score"] for row in result["cases"]) / len(cases)
        elif args.submission:
            report["submission_skipped_reason"] = "Expected suite did not qualify; candidate was not evaluated."
    except Exception as error:
        report["error"] = f"{type(error).__name__}: {error}"
        report["qualified"] = False
    finally:
        _save(args.output_dir / "report.json", report)
    print(json.dumps({key: report[key] for key in ("qualified", "cases_passed", "cases_total", "submission")}, allow_nan=False))
    return 0 if report["qualified"] and "error" not in report else 1


if __name__ == "__main__":
    raise SystemExit(main())
