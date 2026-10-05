"""Run official terminal agents with one public-only MCP execution tool."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile

from dotenv import dotenv_values

from harness.agent import SYSTEM_PROMPT
from harness.config import EXECUTION_TIMEOUT_SECONDS, MAX_AGENT_TURNS, MAX_RUN_CALLS
from harness.executor import run_solution
from harness.providers import gemini_cli, mistral_cli


REPO = Path(__file__).resolve().parent.parent


def audit_events(path: Path, provider: str, model: str) -> dict:
    """Reject observable tool/model changes; keep native events as primary evidence."""
    models = set()
    tools = set()
    result = None
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        event = json.loads(line)
        if event.get("type") == "effect" and event.get("detail", {}).get("toolName"):
            tools.add(event["detail"]["toolName"])
        if event.get("type") == "init" and event.get("model"):
            models.add(event["model"])
        if event.get("type") == "tool_use":
            tools.add(event["tool_name"])
        if event.get("type") == "result":
            result = event
            models.update(event.get("stats", {}).get("models", {}))
        # Vibe emits completed public-history entries, including tool calls.
        message = event.get("message", event)
        for call in message.get("tool_calls", []) or []:
            tools.add(call["function"]["name"])
    for session_path in (path.parent / "native-sessions").glob("*.json"):
        session = json.loads(session_path.read_text())
        models.update(
            message["model"] for message in session.get("messages", [])
            if message.get("type") == "gemini" and message.get("model")
        )
    allowed_tools = {"run_solution", "benchmark_run_solution", "benchmark__run_solution", "mcp_benchmark_run_solution"}
    if tools - allowed_tools:
        raise RuntimeError(f"Unexpected native tools used: {sorted(tools - allowed_tools)}")
    expected = mistral_cli.MODEL_ALIASES.get(model, model) if provider == "mistral" else model
    if models - {model, expected}:
        raise RuntimeError(f"Client changed the requested model: {sorted(models)}")
    if result and result.get("status") == "error":
        raise RuntimeError(f"Client reported failure: {result.get('error')}")
    return {"observed_models": sorted(models), "observed_tools": sorted(tools), "client_result": result}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", choices=["mistral", "gemini"], required=True)
    parser.add_argument("--model", help="Exact CLI model selection; provider defaults are recorded explicitly.")
    parser.add_argument("--workbook", type=Path, required=True)
    parser.add_argument("--workbook-name", default="fcff2st.xlsx", help="Public .xlsx basename specified by the task.")
    parser.add_argument("--task", type=Path, default=REPO / "tasks/damodaran_fcff2st/task.md")
    parser.add_argument("--base-input", type=Path, default=REPO / "tasks/damodaran_fcff2st/inputs/base_case.json")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--mistral-auth-dir", type=Path, help="Isolated VIBE_HOME containing account-login .env credentials.")
    parser.add_argument("--max-steps", type=int, default=MAX_AGENT_TURNS)
    parser.add_argument("--max-run-calls", type=int, default=MAX_RUN_CALLS)
    parser.add_argument("--timeout", type=float, default=EXECUTION_TIMEOUT_SECONDS)
    parser.add_argument("--wall-timeout", type=float, default=900)
    args = parser.parse_args()
    if any(not math.isfinite(value) or value <= 0 for value in (args.max_steps, args.max_run_calls, args.timeout, args.wall_timeout)):
        parser.error("All limits must be finite and positive")
    if Path(args.workbook_name).name != args.workbook_name or Path(args.workbook_name).suffix.lower() != ".xlsx":
        parser.error("--workbook-name must be a single .xlsx filename")
    if args.mistral_auth_dir and args.provider != "mistral":
        parser.error("--mistral-auth-dir applies only to Mistral")
    model = args.model or ("mistral-medium-3.5" if args.provider == "mistral" else gemini_cli.TARGET_MODEL)
    adapter = mistral_cli if args.provider == "mistral" else gemini_cli
    key_name = "MISTRAL_API_KEY" if args.provider == "mistral" else "GEMINI_API_KEY"
    if args.mistral_auth_dir:
        key = dotenv_values(args.mistral_auth_dir / ".env").get(key_name)
        auth_mode = "vibe-account"
    else:
        key = os.environ.get(key_name) or dotenv_values(REPO / ".env").get(key_name)
        auth_mode = "api-key"
    if not key:
        parser.error(f"Missing {key_name} for the selected authentication route")
    public_files = {
        "task.md": args.task.read_bytes(),
        "inputs/base_case.json": args.base_input.read_bytes(),
        args.workbook_name: args.workbook.read_bytes(),
    }
    json.loads(public_files["inputs/base_case.json"])
    started = datetime.now(timezone.utc)
    run_dir = (args.run_dir or REPO / "runs/private" / started.strftime(f"{args.provider}-cli-%Y%m%dT%H%M%S%fZ")).resolve()
    run_dir.mkdir(parents=True, exist_ok=False)
    metadata = {
        "provider": args.provider, "transport": "official-cli-mcp", "requested_model": model,
        "configured_api_model": mistral_cli.MODEL_ALIASES.get(model, model) if args.provider == "mistral" else model,
        "auth_mode": auth_mode, "started_at": started.isoformat(), "status": "running",
        "max_steps": args.max_steps, "max_run_calls": args.max_run_calls,
        "execution_timeout": args.timeout, "wall_timeout": args.wall_timeout,
        "python": sys.executable, "public_sha256": {name: hashlib.sha256(data).hexdigest() for name, data in public_files.items()},
        "generation_settings": {"temperature": 1.0, "thinking": "high"} if args.provider == "mistral" else "CLI defaults",
    }
    metadata_path = run_dir / "metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2))
    print(f"Run directory: {run_dir}", flush=True)
    exit_code = 1
    try:
        with tempfile.TemporaryDirectory(prefix="fcff-terminal-", dir="/private/tmp") as tmp:
            root = Path(tmp)
            workspace, control, settings = (root / name for name in ("public", "control", "settings"))
            workspace.mkdir()
            control.mkdir()
            for name, data in public_files.items():
                target = workspace / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
            # Prove workbook imports and sandbox startup before using model quota.
            probe = workspace / "solution.py"
            probe.write_text(f"import openpyxl\nw = openpyxl.load_workbook({args.workbook_name!r}, read_only=True)\nprint(w.sheetnames)\n")
            preflight = run_solution(str(probe), timeout=args.timeout)
            (run_dir / "runtime-preflight.json").write_text(json.dumps(preflight, indent=2))
            probe.unlink()
            if preflight["exit_code"] != 0:
                raise RuntimeError(f"Python runtime preflight failed: {preflight['stderr']}")
            prompt = SYSTEM_PROMPT.format(workbook_name=args.workbook_name) + f"\nLimits: {args.max_steps} model turns, {args.max_run_calls} executions, {args.timeout} seconds per execution.\n\n" + public_files["task.md"].decode()
            (run_dir / "prompt.txt").write_text(prompt)
            mcp_command = [sys.executable, str(REPO / "harness/mcp_server.py"), "--workspace", str(workspace), "--run-dir", str(run_dir), "--max-run-calls", str(args.max_run_calls), "--timeout", str(args.timeout)]
            command, additions = adapter.build_command(control, settings, prompt, model, mcp_command, args.max_steps)
            for name in ("config.toml", "settings.json", "system-defaults.json"):
                config_path = settings / name
                if config_path.is_file():
                    (run_dir / name).write_bytes(config_path.read_bytes())
            environment = {name: os.environ[name] for name in ("PATH", "LANG", "LC_ALL", "TMPDIR") if name in os.environ}
            environment.update({"HOME": str(settings), "TERM": "dumb", "NO_COLOR": "1", "VIBE_TEST_DISABLE_KEYRING": "1", key_name: key})
            environment.update(additions)
            version = subprocess.run([command[0], "--version"], env=environment, cwd=control, text=True, capture_output=True, timeout=30, stdin=subprocess.DEVNULL)
            if version.returncode:
                raise RuntimeError(f"CLI version check failed: {version.stderr}")
            metadata["cli_version"] = version.stdout.strip()
            metadata_path.write_text(json.dumps(metadata, indent=2))
            events_path = run_dir / "cli-events.jsonl"
            solution = workspace / "solution.py"
            with events_path.open("w") as out, (run_dir / "cli-stderr.txt").open("w") as err:
                proc = subprocess.Popen(command, env=environment, cwd=control, stdin=subprocess.DEVNULL, stdout=out, stderr=err, start_new_session=True)
                try:
                    metadata["cli_exit_code"] = proc.wait(timeout=args.wall_timeout)
                finally:
                    # Kill lingering CLI/MCP children before freezing any candidate bytes.
                    try:
                        os.killpg(proc.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    proc.wait()
                    for session_path in settings.glob(".gemini/tmp/*/chats/session-*.json"):
                        destination = run_dir / "native-sessions" / session_path.name
                        destination.parent.mkdir(exist_ok=True)
                        destination.write_bytes(session_path.read_bytes())
                    if solution.is_file() and not solution.is_symlink():
                        (run_dir / "partial-solution.py").write_bytes(solution.read_bytes())
            if metadata["cli_exit_code"] != 0:
                raise RuntimeError(f"CLI exited {metadata['cli_exit_code']}; see cli-stderr.txt and cli-events.jsonl")
            metadata.update(audit_events(events_path, args.provider, model))
            state_path = run_dir / "execution-state.json"
            if not state_path.is_file() or not solution.is_file() or solution.is_symlink():
                raise RuntimeError("Client did not save a regular solution.py through the benchmark tool")
            metadata["run_calls"] = json.loads(state_path.read_text())["run_calls"]
            frozen = solution.read_bytes()
            (run_dir / "solution.py").write_bytes(frozen)
            (run_dir / "partial-solution.py").unlink()
            metadata["solution_sha256"] = hashlib.sha256(frozen).hexdigest()
            metadata["status"] = "frozen"
            exit_code = 0
    except Exception as exc:
        metadata["status"] = "failed"
        metadata["error"] = f"{type(exc).__name__}: {exc}"
        print(metadata["error"], file=sys.stderr, flush=True)
    finally:
        metadata["finished_at"] = datetime.now(timezone.utc).isoformat()
        metadata_path.write_text(json.dumps(metadata, indent=2))
    if exit_code == 0:
        print(f"Frozen submission: {run_dir / 'solution.py'}", flush=True)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
