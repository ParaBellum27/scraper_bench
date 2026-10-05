"""Execute and grade a one-file financial benchmark submission in a subprocess.

Candidate contract:
    python solution.py
reads one JSON input object from stdin and writes one JSON output object to stdout.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Any, Dict, Tuple

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(REPO))

from evaluator.benchmarks import BENCHMARKS
from evaluator.grader import grade_case, summarize
from evaluator.pierre_lbo_cases import exercised_features
from harness.executor import run_solution


def _reject_nonfinite(value: str):
    raise ValueError(f"nonstandard JSON number: {value}")


def _finite_json_float(value: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("JSON number exceeds finite floating-point range")
    return number


def run_submission(path: Path, inputs: Dict[str, Any], timeout: float) -> Tuple[Dict[str, Any] | None, str | None]:
    try:
        # Every case gets a new outside-repo workspace: no workbook, task,
        # public input file, prior-case scratch, or hidden grading artifacts.
        with tempfile.TemporaryDirectory(prefix="finance-grade-", dir="/private/tmp") as directory:
            solution = Path(directory) / "solution.py"
            shutil.copyfile(path, solution)
            result = run_solution(str(solution), timeout=timeout, stdin=json.dumps(inputs))
    except Exception as exc:
        return None, f"execution failed: {exc}"

    if result["exit_code"] == 124:
        return None, f"timeout after {timeout:.1f}s"
    if result["exit_code"] != 0:
        err = result["stderr"].strip()[-1200:]
        return None, f"non-zero exit {result['exit_code']}: {err}"
    try:
        return json.loads(result["stdout"], parse_constant=_reject_nonfinite, parse_float=_finite_json_float), None
    except (json.JSONDecodeError, ValueError) as exc:
        return None, f"invalid JSON output: {exc}; stdout={result['stdout'][-500:]!r}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("submission", type=Path)
    parser.add_argument("--benchmark", choices=BENCHMARKS, default="damodaran_fcff2st")
    parser.add_argument(
        "--base-input",
        type=Path,
        help="Override the selected benchmark's public base input.",
    )
    parser.add_argument("--seed", type=int, help="Override BENCH_SEED or the selected benchmark's seed.")
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument("--summary-only", action="store_true")
    args = parser.parse_args()

    benchmark = BENCHMARKS[args.benchmark]
    base_path = args.base_input or benchmark.base_input(REPO, args.benchmark)
    seed = args.seed if args.seed is not None else int(os.environ.get("BENCH_SEED", str(benchmark.seed)))
    base = json.loads(base_path.read_text())
    cases = benchmark.cases(base, seed=seed)
    if len(cases) != benchmark.hidden_case_count:
        raise ValueError(f"Expected {benchmark.hidden_case_count} hidden cases, got {len(cases)}")
    submission_hash = hashlib.sha256(args.submission.read_bytes()).hexdigest()
    base_expected = benchmark.reference(base)
    base_actual, base_err = run_submission(args.submission.resolve(), base, args.timeout)
    base_result = grade_case(
        "base_case", base_actual, base_expected, base_err,
        scoring_groups=benchmark.scoring_groups, rel_tol=benchmark.rel_tol, abs_tol=benchmark.abs_tol,
    )

    hidden_results = []
    feature_map = {}
    for case in cases:
        expected = benchmark.reference(case["inputs"])
        if args.benchmark == "pierre_lbo":
            feature_map[case["name"]] = exercised_features(case["inputs"], expected)
        actual, err = run_submission(args.submission.resolve(), case["inputs"], args.timeout)
        hidden_results.append(grade_case(
            case["name"], actual, expected, err, scoring_groups=benchmark.scoring_groups,
            rel_tol=benchmark.rel_tol, abs_tol=benchmark.abs_tol,
        ))

    report = summarize(base_result, hidden_results)
    if hashlib.sha256(args.submission.read_bytes()).hexdigest() != submission_hash:
        raise RuntimeError("Submission changed during grading; refusing a mixed-source report")
    report["submission_sha256"] = submission_hash
    report["grading_timeout_seconds"] = args.timeout
    if args.benchmark == "pierre_lbo":
        report["base_case"]["exercised_features"] = exercised_features(base, base_expected)
        for result in report["hidden_cases"]:
            result["exercised_features"] = feature_map[result["name"]]
    report.update(benchmark=args.benchmark, seed=seed, rel_tol=benchmark.rel_tol, abs_tol=benchmark.abs_tol)
    if args.summary_only:
        report = {
            k: report[k]
            for k in [
                "primary_metric",
                "hidden_cases_fully_correct",
                "hidden_cases_total",
                "all_hidden_cases_correct",
                "base_case_fully_correct",
                "all_cases_correct",
                "score_role",
                "score",
                "base_case_score",
                "hidden_average_score",
                "submission_sha256",
            ]
        }
    print(json.dumps(report, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
