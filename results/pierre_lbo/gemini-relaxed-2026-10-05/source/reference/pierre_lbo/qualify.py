"""Reconcile independently recalculated Excel formulas with the Python oracle.

Run from the repository root with Excel on macOS, or explicitly select LibreOffice:
    python -m reference.pierre_lbo.qualify --engine excel --output-dir runs/private/pierre_lbo/qualification
    python -m reference.pierre_lbo.qualify --engine libreoffice --soffice /path/to/soffice --output-dir runs/private/pierre_lbo/qualification-calc

Creates new derivative workbooks only. Never recalculates the supplied original,
changes application calculation/alert settings, or saves/closes unrelated books.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any

from evaluator.benchmarks import BENCHMARKS
from evaluator.grader import grade_case
from reference.pierre_lbo.workbook import build_workbook, read_workbook_outputs


_EXCEL_SCRIPT = '''on run argv
    set targetPath to item 1 of argv
    set targetName to item 2 of argv
    with timeout of 120 seconds
        tell application "Microsoft Excel"
            if exists workbook targetName then error "Refusing to touch an already-open workbook: " & targetName
            set modelBook to open workbook workbook file name targetPath update links do not update links read only false add to mru false
            try
                repeat with sheetName in {"Inputs", "Scenarios", "Forecast", "Debt", "Returns"}
                    calculate worksheet (contents of sheetName) of modelBook
                end repeat
                save modelBook
                close modelBook saving no
            on error errorText number errorNumber
                close modelBook saving no
                error errorText number errorNumber
            end try
            return version
        end tell
    end timeout
end run
'''


def _recalculate(path: Path) -> str:
    if sys.platform != "darwin":
        raise RuntimeError("Native Excel qualification currently requires macOS")
    process = subprocess.run(
        ["osascript", "-", str(path.resolve()), path.name], input=_EXCEL_SCRIPT,
        capture_output=True, text=True, timeout=150,
    )
    if process.returncode:
        raise RuntimeError(process.stderr.strip())
    return process.stdout.strip()


def _convert_with_libreoffice(path: Path, executable: str) -> Path:
    output_dir = path.parent / "calculated"
    output_dir.mkdir(exist_ok=True)
    destination = output_dir / path.name
    if destination.exists():
        raise FileExistsError(f"Refusing to replace calculated workbook: {destination}")
    with tempfile.TemporaryDirectory(prefix="pierre-lbo-calc-") as profile:
        process = subprocess.run(
            [executable, f"-env:UserInstallation={Path(profile).resolve().as_uri()}",
             "--headless", "--norestore", "--convert-to", "xlsx:Calc MS Excel 2007 XML",
             "--outdir", str(output_dir.resolve()), str(path.resolve())],
            capture_output=True, text=True, timeout=150,
        )
    if process.returncode or not destination.is_file():
        raise RuntimeError(f"LibreOffice conversion failed: {process.stdout}\n{process.stderr}")
    return destination


def _validate_diagnostics(diagnostics, cases, required_fields) -> None:
    if not isinstance(diagnostics, list) or not diagnostics:
        raise ValueError("Qualification requires nonempty independent arithmetic diagnostics")
    names = {case["name"] for case in cases}
    for case in diagnostics:
        if (not isinstance(case, dict)
                or not {"name", "inputs", "expected", "rel_tol", "abs_tol"} <= set(case)
                or not isinstance(case["name"], str) or not case["name"]
                or not isinstance(case["inputs"], dict)
                or not isinstance(case["expected"], dict) or not case["expected"]
                or not set(case["expected"]) <= set(required_fields)):
            raise ValueError("Every diagnostic requires inputs and a nonempty expected subset of scored fields")
        if case["name"] in names:
            raise ValueError("Scored and diagnostic workbook names must be distinct")
        names.add(case["name"])


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    benchmark = BENCHMARKS["pierre_lbo"]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-input", type=Path, default=benchmark.base_input(root, "pierre_lbo"))
    parser.add_argument("--seed", type=int, default=benchmark.seed)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--engine", choices=("excel", "libreoffice"), default="excel")
    parser.add_argument("--soffice", default="soffice", help="LibreOffice executable when explicitly selected.")
    args = parser.parse_args()
    engine_version = None
    if args.engine == "libreoffice":
        engine_version = subprocess.run(
            [args.soffice, "--version"], capture_output=True, text=True, check=True, timeout=30,
        ).stdout.strip()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    base = json.loads(args.base_input.read_text())
    cases: list[dict[str, Any]] = [{"name": "base_case", "inputs": base}, *benchmark.cases(base, seed=args.seed)]
    if len(cases) != 1 + benchmark.hidden_case_count or len({case["name"] for case in cases}) != len(cases):
        raise ValueError("Qualification requires the base case and every distinct hidden case")
    required_fields = [field for _, fields in benchmark.scoring_groups.values() for field in fields]
    if len(required_fields) != 55 or len(set(required_fields)) != 55:
        raise ValueError("Pierre qualification requires exactly 55 distinct scored fields")
    diagnostics_path = root / "reference/pierre_lbo/hand_examples.json"
    diagnostics = json.loads(diagnostics_path.read_text())
    _validate_diagnostics(diagnostics, cases, required_fields)
    diagnostic_results: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []
    for case in [*cases, *diagnostics]:
        name, inputs = case["name"], case["inputs"]
        path = args.output_dir / f"{name}.xlsx"
        try:
            expected = benchmark.reference(inputs)
            if set(expected) != set(required_fields):
                raise ValueError("Reference output does not match the 55-field scoring contract")
            build_workbook(inputs, path)
            if args.engine == "excel":
                engine_version = _recalculate(path)
            else:
                path = _convert_with_libreoffice(path, args.soffice)
            actual = read_workbook_outputs(path)
            grade = grade_case(name, actual, expected, scoring_groups=benchmark.scoring_groups,
                               rel_tol=benchmark.rel_tol, abs_tol=benchmark.abs_tol)
            passed = not grade.missing_fields and not grade.mismatches and set(actual) == set(expected)
            hand_grades = {}
            if "expected" in case:
                for implementation, output in (("reference", expected), ("spreadsheet", actual)):
                    hand_grade = grade_case(
                        name, output, case["expected"],
                        scoring_groups={"independent_arithmetic": (1.0, list(case["expected"]))},
                        rel_tol=case["rel_tol"], abs_tol=case["abs_tol"],
                    )
                    hand_grades[implementation] = asdict(hand_grade)
                    passed = passed and not hand_grade.missing_fields and not hand_grade.mismatches
            target = diagnostic_results if "expected" in case else results
            target.append({"name": name, "passed": passed, "engine": args.engine, "engine_version": engine_version,
                           "workbook": str(path), "workbook_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                           "inputs": inputs, "expected": expected, "spreadsheet": actual, "grade": asdict(grade),
                           "fields_compared": len(required_fields), "hand_grades": hand_grades})
            print(f"{name}: {'PASS' if passed else 'FAIL'}", flush=True)
        except Exception as error:
            target = diagnostic_results if "expected" in case else results
            target.append({"name": name, "passed": False, "error": f"{type(error).__name__}: {error}"})
            print(f"{name}: ERROR {error}", flush=True)
    sources = ("reference/pierre_lbo/reference.py", "reference/pierre_lbo/workbook.py",
               "reference/pierre_lbo/qualify.py", "evaluator/pierre_lbo_cases.py", "evaluator/grader.py",
               "evaluator/benchmarks.py", "reference/pierre_lbo/hand_examples.json", "tasks/pierre_lbo/task.md")
    report = {"benchmark": "pierre_lbo", "created_at": datetime.now(timezone.utc).isoformat(),
              "engine": args.engine, "engine_version": engine_version,
              "seed": args.seed, "rel_tol": benchmark.rel_tol, "abs_tol": benchmark.abs_tol,
              "base_input_sha256": hashlib.sha256(args.base_input.read_bytes()).hexdigest(),
              "source_sha256": {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in sources},
              "cases_passed": sum(row["passed"] for row in results), "cases_total": len(results),
              "qualified": all(row["passed"] for row in results + diagnostic_results),
              "cases": results, "diagnostics": diagnostic_results,
              "diagnostics_passed": sum(row["passed"] for row in diagnostic_results),
              "diagnostics_total": len(diagnostic_results)}
    (args.output_dir / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({key: report[key] for key in ("qualified", "cases_passed", "cases_total")}))
    return 0 if report["qualified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
