"""Rebuild deliberate-error controls from the current oracle and grade offline.

python -m reference.pierre_lbo.controls --output-dir runs/private/pierre_lbo/controls-audit
These programs are validation controls, never candidate-model submissions.
"""
from __future__ import annotations

import argparse
import ast
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from reference.pierre_lbo.reference import value_lbo


def _assignment_target(expression: str) -> str:
    statement = ast.parse(expression + " = None").body[0]
    if not isinstance(statement, ast.Assign):
        raise ValueError("Control target must be an assignment")
    return ast.dump(statement.targets[0])


class _Mutation(ast.NodeTransformer):
    def __init__(self, replacements):
        self.replacements = {
            _assignment_target(target): ast.parse(value, mode="eval").body
            for target, value in replacements.items()
        }
        self.hits = {target: 0 for target in self.replacements}

    def visit_Assign(self, node):
        if len(node.targets) == 1:
            target = ast.dump(node.targets[0])
            if target in self.replacements:
                node.value = deepcopy(self.replacements[target])
                self.hits[target] += 1
        return self.generic_visit(node)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    source = (root / "reference/pierre_lbo/reference.py").read_text()
    base = json.loads((root / "tasks/pierre_lbo/inputs/base_case.json").read_text())
    args.output_dir.mkdir(parents=True, exist_ok=False)
    programs = {
        "reference": source,
        "constant_base": "import json\nprint(json.dumps(" + repr(value_lbo(base)) + "))\n",
    }
    mutations = {
        "ignore_cash_interest": {"tlb_interest": "0.0", "rcf_interest": "0.0"},
        "ignore_cash_sweep": {"sweep": "0.0"},
        "ignore_preferred_priority": {"out['preferred_payout']": "0.0"},
        "integer_year_irr": {
            "out[owner + '_irr']":
                "(proceeds / investment) ** (1 / inputs['exit_period']) - 1 "
                "if investment > 0 and proceeds > 0 else None",
        },
    }
    for name, replacements in mutations.items():
        mutation = _Mutation(replacements)
        tree = mutation.visit(ast.parse(source))
        if any(count != 1 for count in mutation.hits.values()):
            raise RuntimeError(f"Control mutation no longer uniquely matches oracle: {name}: {mutation.hits}")
        programs[name] = ast.unparse(ast.fix_missing_locations(tree)) + "\n"
    summaries = []
    for name, program in programs.items():
        path = args.output_dir / f"{name}.py"
        path.write_text(program)
        process = subprocess.run(
            [sys.executable, "-m", "evaluator.run_grader", str(path.resolve()),
             "--benchmark", "pierre_lbo", "--seed", "20261004", "--timeout", "5"],
            cwd=root, capture_output=True, text=True, check=True,
        )
        report = json.loads(process.stdout)
        (args.output_dir / f"{name}.grade.json").write_text(process.stdout)
        summary = {"control": name, **{key: value for key, value in report.items()
                                      if key not in ("base_case", "hidden_cases")}}
        summary["program_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        summaries.append(summary)
        print(f"{name}: {report['hidden_cases_fully_correct']}/{report['hidden_cases_total']} fully correct; "
              f"all={report['all_hidden_cases_correct']}; diagnostic score={report['score']:.6f}", flush=True)
    (args.output_dir / "summary.json").write_text(json.dumps(summaries, indent=2, allow_nan=False) + "\n")
    if not summaries[0]["all_cases_correct"]:
        raise RuntimeError("Reference control failed")
    if any(row["all_hidden_cases_correct"] for row in summaries[1:]):
        raise RuntimeError("A deliberately flawed control escaped all hidden scenarios")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
