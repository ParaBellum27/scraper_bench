"""Host-only execution accounting and explicit, immutable source submissions."""

from __future__ import annotations

import fcntl
import hashlib
import json
from pathlib import Path
from typing import Any

from harness.executor import run_solution, validate_runtime_separation


class SubmissionSession:
    def __init__(self, workspace: Path, run_dir: Path, base_input: str, max_run_calls: int, timeout: float):
        self.workspace = workspace.resolve(strict=True)
        self.run_dir = run_dir.resolve(strict=True)
        if self.workspace == self.run_dir or self.workspace in self.run_dir.parents or self.run_dir in self.workspace.parents:
            raise ValueError("Public workspace and private run directory must be disjoint")
        validate_runtime_separation(self.run_dir)
        validate_runtime_separation(self.workspace)
        self.max_run_calls = max_run_calls
        self.timeout = timeout
        self.state_path = self.run_dir / "execution-state.json"
        self.lock_path = self.run_dir / "execution-state.lock"
        with self.lock_path.open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            snapshot = self.run_dir / "public-base-input.json"
            if not snapshot.exists():
                snapshot.write_text(base_input)
            self.base_input = snapshot.read_text()

    def execute(self, code: str, submit: bool = False) -> dict:
        if not isinstance(code, str) or type(submit) is not bool:
            return {"error": "run_solution requires string code and boolean submit arguments."}
        with self.lock_path.open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            state: dict[str, Any] = json.loads(self.state_path.read_text()) if self.state_path.exists() else {"run_calls": 0}
            if state["run_calls"] >= self.max_run_calls:
                return {"error": "Execution limit reached; only the last explicit submission is final.", "remaining": 0}
            count = state["run_calls"] + 1
            source = code.encode("utf-8")
            digest = hashlib.sha256(source).hexdigest()
            # Exclusive host-owned snapshots are never collected from candidate files.
            with (self.run_dir / f"step-{count:02d}.py").open("xb") as snapshot:
                snapshot.write(source)
            state["run_calls"] = count
            if submit:
                state["submission"] = {"run_call": count, "sha256": digest}
            temporary = self.state_path.with_suffix(".tmp")
            temporary.write_text(json.dumps(state))
            temporary.replace(self.state_path)
            solution = self.workspace / "solution.py"
            try:
                # A previous program may leave a symlink or directory here. Never follow it.
                solution.unlink(missing_ok=True)
                solution.write_bytes(source)
                result = run_solution(str(solution), timeout=self.timeout, stdin=self.base_input)
            except OSError as exc:
                result = {"exit_code": 125, "stdout": "", "stderr": f"Workspace preparation failed: {exc}"}
            result.update({"run_call": count, "remaining": self.max_run_calls - count,
                           "submitted": submit, "submission": state.get("submission")})
            with (self.run_dir / "executions.jsonl").open("a") as log:
                log.write(json.dumps({"run_call": count, "source_sha256": digest, "submit": submit, "result": result}) + "\n")
            return result


def freeze_submission(run_dir: Path) -> dict:
    """Collect only an explicit host snapshot; absence is an ungraded attempt."""
    with (run_dir / "execution-state.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state_path = run_dir / "execution-state.json"
        state = json.loads(state_path.read_text()) if state_path.exists() else {}
        submission = state.get("submission")
        if not submission:
            raise RuntimeError("No explicit submission: call run_solution(code, submit=True); attempt is ungraded")
        source_path = run_dir / f"step-{submission['run_call']:02d}.py"
        if source_path.is_symlink() or not source_path.is_file():
            raise RuntimeError("Submitted host snapshot is not a regular file")
        source = source_path.read_bytes()
        if hashlib.sha256(source).hexdigest() != submission["sha256"]:
            raise RuntimeError("Submitted host snapshot hash mismatch")
        destination = run_dir / "solution.py"
        with destination.open("xb") as frozen:
            frozen.write(source)
        return {"solution_sha256": submission["sha256"], "submission_run_call": submission["run_call"],
                "run_calls": state["run_calls"]}
