"""Offline synthetic reference smoke; no model/provider requests."""
import asyncio
import json
from pathlib import Path
import sys
import tempfile
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))


from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import TextContent

from evaluator.benchmarks import BENCHMARKS
from evaluator.grader import grade_case
from evaluator.run_grader import run_submission
from harness.submission import freeze_submission


async def main():
    root = Path.cwd()
    public = root / "tasks/pierre_lbo"
    source = (root / "reference/pierre_lbo/reference.py").read_text()
    inputs = json.loads((public / "inputs/base_case.json").read_text())
    qualification = json.loads((root / "results/pierre_lbo/audit-2026-10-05/qualification.json").read_text())
    expected = next(row["spreadsheet"] for row in qualification["cases"] if row["name"] == "base_case")
    with tempfile.TemporaryDirectory(dir="/private/tmp") as temporary:
        workspace, private = (Path(temporary) / name for name in ("public", "private"))
        workspace.mkdir()
        private.mkdir()
        for name in ("task.md", "inputs/base_case.json", "pierre_lbo_one.xlsx"):
            path = workspace / name
            path.parent.mkdir(exist_ok=True)
            path.write_bytes((public / name).read_bytes())
        parameters = StdioServerParameters(command=sys.executable, args=[
            str(root / "harness/mcp_server.py"), "--workspace", str(workspace),
            "--run-dir", str(private), "--max-run-calls", "3", "--timeout", "10",
        ])
        async with stdio_client(parameters) as streams:
            async with ClientSession(*streams) as session:
                await session.initialize()
                tools = await session.list_tools()
                assert [tool.name for tool in tools.tools] == ["run_solution"]
                codes = [
                    ("import json,openpyxl\nw=openpyxl.load_workbook('pierre_lbo_one.xlsx',read_only=True)\nprint(json.dumps(w.sheetnames))\n", False),
                    (source, True),
                    ("from pathlib import Path\nPath('solution.py').write_text('inspection must not become final')\nprint('inspection')\n", False),
                ]
                results = []
                for code, submit in codes:
                    result = await session.call_tool("run_solution", {"code": code, "submit": submit})
                    assert not result.isError, result
                    content = result.content[0]
                    assert isinstance(content, TextContent), content
                    execution = json.loads(content.text)
                    assert execution["exit_code"] == 0, execution
                    results.append(execution)
        frozen = freeze_submission(private)
        assert (private / "solution.py").read_text() == source
        actual, error = run_submission(private / "solution.py", inputs, 5)
        assert isinstance(actual, dict), error
        benchmark = BENCHMARKS["pierre_lbo"]
        grade = grade_case("frozen_reference", actual, expected, error,
                           scoring_groups=benchmark.scoring_groups,
                           rel_tol=benchmark.rel_tol, abs_tol=benchmark.abs_tol)
        assert not grade.execution_error and not grade.missing_fields and not grade.mismatches, grade
        assert set(actual) == set(expected) and len(actual) == 55
        print(json.dumps({
            "kind": "synthetic_reference_infrastructure_check", "provider_requests": 0,
            "workbook_sheets": json.loads(results[0]["stdout"]),
            "tools": [tool.name for tool in tools.tools],
            "accepted_calls": len(results), "remaining": results[-1]["remaining"],
            "explicit_submission_preserved_after_inspection_and_mutation": True,
            "frozen": frozen, "fields_matched_to_independent_spreadsheet": len(actual),
            "grading_execution_error": error, "grading_mismatches": grade.mismatches,
        }, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
