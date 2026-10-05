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
    results: list[dict[str, Any]] = []
    for case in cases:
        name, inputs = case["name"], case["inputs"]
        path = args.output_dir / f"{name}.xlsx"
        try:
            expected = benchmark.reference(inputs)
            build_workbook(inputs, path)
            if args.engine == "excel":
                engine_version = _recalculate(path)
            else:
                path = _convert_with_libreoffice(path, args.soffice)
            actual = read_workbook_outputs(path)
            grade = grade_case(name, actual, expected, scoring_groups=benchmark.scoring_groups,
                               rel_tol=benchmark.rel_tol, abs_tol=benchmark.abs_tol)
            passed = not grade.missing_fields and not grade.mismatches and set(actual) == set(expected)
            results.append({"name": name, "passed": passed, "engine": args.engine, "engine_version": engine_version,
                            "workbook": str(path), "workbook_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                            "inputs": inputs, "expected": expected, "spreadsheet": actual, "grade": asdict(grade)})
            print(f"{name}: {'PASS' if passed else 'FAIL'}", flush=True)
        except Exception as error:
            results.append({"name": name, "passed": False, "error": f"{type(error).__name__}: {error}"})
            print(f"{name}: ERROR {error}", flush=True)
    sources = ("reference/pierre_lbo/reference.py", "reference/pierre_lbo/workbook.py",
               "reference/pierre_lbo/qualify.py", "evaluator/pierre_lbo_cases.py", "evaluator/grader.py",
               "evaluator/benchmarks.py")
    report = {"benchmark": "pierre_lbo", "created_at": datetime.now(timezone.utc).isoformat(),
              "engine": args.engine, "engine_version": engine_version,
              "seed": args.seed, "rel_tol": benchmark.rel_tol, "abs_tol": benchmark.abs_tol,
              "base_input_sha256": hashlib.sha256(args.base_input.read_bytes()).hexdigest(),
              "source_sha256": {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in sources},
              "cases_passed": sum(row["passed"] for row in results), "cases_total": len(results),
              "qualified": all(row["passed"] for row in results), "cases": results}
    (args.output_dir / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({key: report[key] for key in ("qualified", "cases_passed", "cases_total")}))
    return 0 if report["qualified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
