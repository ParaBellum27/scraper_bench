"""Expose only sandboxed public-case execution to terminal coding agents."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Annotated

from pydantic import Field, StrictBool, StrictStr

# The host launches this file from a clean control directory outside the repo.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp.server.fastmcp import FastMCP

from harness.submission import SubmissionSession


def create_server(workspace: Path, run_dir: Path, max_run_calls: int, timeout: float) -> FastMCP:
    workspace = workspace.resolve(strict=True)
    run_dir = run_dir.resolve(strict=True)
    input_snapshot = run_dir / "public-base-input.json"
    base_input = input_snapshot.read_text() if input_snapshot.exists() else (workspace / "inputs/base_case.json").read_text()
    session = SubmissionSession(workspace, run_dir, base_input, max_run_calls, timeout)
    server = FastMCP("benchmark", log_level="WARNING")

    @server.tool(name="run_solution")
    def execute(code: StrictStr, submit: Annotated[StrictBool, Field(description="Explicitly replace the final submission with these exact source bytes.")] = False) -> str:
        """Execute Python with the public JSON on stdin; default is inspection only.

        The workspace contains task.md, the task's .xlsx workbook, and inputs/base_case.json.
        Python's standard library and openpyxl are available. Use submit=True for
        your standalone final program: only the last explicit submission is graded.
        Its exact source is protected before execution, even if execution fails.
        Later inspection calls and workspace writes cannot alter that snapshot.
        No explicit submission means an ungraded attempt. Every accepted execution
        consumes one call, including submissions; reserve a call to submit.
        Returns exit_code, stdout, stderr, and submission/budget status.
        No network, private grading files, or credentials are available.
        """
        return json.dumps(session.execute(code, submit))

    return server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--max-run-calls", type=int, default=12)
    parser.add_argument("--timeout", type=float, default=10)
    args = parser.parse_args()
    if args.max_run_calls <= 0 or args.timeout <= 0:
        parser.error("Execution limits must be positive")
    create_server(args.workspace, args.run_dir, args.max_run_calls, args.timeout).run(transport="stdio")


if __name__ == "__main__":
    main()
