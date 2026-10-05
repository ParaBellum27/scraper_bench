"""Expose only sandboxed public-case execution to terminal coding agents."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
from pathlib import Path
import sys

# The host launches this file from a clean control directory outside the repo.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp.server.fastmcp import FastMCP

from harness.executor import run_solution


def create_server(workspace: Path, run_dir: Path, max_run_calls: int, timeout: float) -> FastMCP:
    workspace = workspace.resolve(strict=True)
    run_dir = run_dir.resolve(strict=True)
    input_snapshot = run_dir / "public-base-input.json"
    with (run_dir / "execution-state.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if not input_snapshot.exists():
            input_snapshot.write_bytes((workspace / "inputs/base_case.json").read_bytes())
        base_input = input_snapshot.read_text()
    state_path = run_dir / "execution-state.json"
    server = FastMCP("benchmark", log_level="WARNING")

    @server.tool(name="run_solution")
    def execute(code: str) -> str:
        """Replace solution.py with complete Python source and execute the public input.

        The workspace contains task.md, the task's .xlsx workbook, and inputs/base_case.json.
        Use Python (including openpyxl) to inspect those public artifacts. Every
        call overwrites solution.py. The last saved file is the final submission.
        Execution receives the public JSON on stdin and returns exit_code,
        stdout, and stderr. The final program must work without any other files.
        There is no network or access to private grading files or credentials.
        """
        # Serialize even if a client issues parallel calls or restarts its server.
        with (run_dir / "execution-state.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            count = json.loads(state_path.read_text())["run_calls"] if state_path.exists() else 0
            if count >= max_run_calls:
                return json.dumps({"error": "Execution limit reached; last saved solution.py is final.", "remaining": 0})
            count += 1
            state_path.write_text(json.dumps({"run_calls": count}))
            source_path = run_dir / f"step-{count:02d}.py"
            source_path.write_text(code)
            solution = workspace / "solution.py"
            # Do not follow a symlink created by the previous candidate program.
            solution.unlink(missing_ok=True)
            solution.write_text(code)
            result = run_solution(str(solution), timeout=timeout, stdin=base_input)
            record = {
                "run_call": count,
                "source_sha256": hashlib.sha256(code.encode()).hexdigest(),
                "result": result,
            }
            with (run_dir / "executions.jsonl").open("a") as log:
                log.write(json.dumps(record) + "\n")
            return json.dumps({**result, "run_call": count, "remaining": max_run_calls - count})

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
