"""Execute and grade a one-file financial benchmark submission in a subprocess.

Candidate contract:
    python solution.py
reads one JSON input object from stdin and writes one JSON output object to stdout.
"""
from __future__ import annotations

import argparse
import json
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
from harness.executor import run_solution


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
        return json.loads(result["stdout"]), None
    except json.JSONDecodeError as exc:
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
    base_expected = benchmark.reference(base)
    base_actual, base_err = run_submission(args.submission.resolve(), base, args.timeout)
    base_result = grade_case(
        "base_case", base_actual, base_expected, base_err,
        scoring_groups=benchmark.scoring_groups, rel_tol=benchmark.rel_tol, abs_tol=benchmark.abs_tol,
    )

    hidden_results = []
    for case in benchmark.cases(base, seed=seed):
        expected = benchmark.reference(case["inputs"])
        actual, err = run_submission(args.submission.resolve(), case["inputs"], args.timeout)
        hidden_results.append(grade_case(
            case["name"], actual, expected, err, scoring_groups=benchmark.scoring_groups,
            rel_tol=benchmark.rel_tol, abs_tol=benchmark.abs_tol,
        ))

    report = summarize(base_result, hidden_results)
    report.update(benchmark=args.benchmark, seed=seed, rel_tol=benchmark.rel_tol, abs_tol=benchmark.abs_tol)
    if args.summary_only:
        report = {
            k: report[k]
            for k in [
                "score",
                "base_case_score",
                "base_case_fully_correct",
                "hidden_average_score",
                "hidden_cases_passed_95",
                "hidden_cases_fully_correct",
                "hidden_cases_total",
            ]
        }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
