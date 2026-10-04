"""Execute and grade a one-file Task 001 submission in a subprocess.

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

from evaluator.grader import grade_case, summarize
from evaluator.hidden_cases import generate_hidden_cases
from harness.executor import run_solution
from reference.damodaran_fcff2st.reference import value_company


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
    parser.add_argument(
        "--base-input",
        type=Path,
        default=REPO / "tasks/damodaran_fcff2st/inputs/base_case.json",
    )
    parser.add_argument("--seed", type=int, default=int(os.environ.get("BENCH_SEED", "20261003")))
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument("--summary-only", action="store_true")
    args = parser.parse_args()

    base = json.loads(args.base_input.read_text())
    base_expected = value_company(base)
    base_actual, base_err = run_submission(args.submission.resolve(), base, args.timeout)
    base_result = grade_case("base_case", base_actual, base_expected, base_err)

    hidden_results = []
    for case in generate_hidden_cases(base, seed=args.seed):
        expected = value_company(case["inputs"])
        actual, err = run_submission(args.submission.resolve(), case["inputs"], args.timeout)
        hidden_results.append(grade_case(case["name"], actual, expected, err))

    report = summarize(base_result, hidden_results)
    if args.summary_only:
        report = {
            k: report[k]
            for k in [
                "score",
                "base_case_score",
                "hidden_average_score",
                "hidden_cases_passed_95",
                "hidden_cases_total",
            ]
        }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
