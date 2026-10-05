import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

from dotenv import load_dotenv

from harness.agent import Agent
from harness.config import EXECUTION_TIMEOUT_SECONDS, MAX_AGENT_TURNS, MAX_RUN_CALLS, MODELS
from harness.providers.mistral import MistralProvider


REPO = Path(__file__).resolve().parent.parent


def main():
    load_dotenv(REPO / ".env")
    parser = argparse.ArgumentParser(description="Run a public-only Mistral coding trial.")
    parser.add_argument("--provider", choices=["mistral"], default="mistral")
    parser.add_argument("--model", default=MODELS["mistral_medium_3_5"].model)
    parser.add_argument("--task", type=Path, default=REPO / "tasks/damodaran_fcff2st/task.md")
    parser.add_argument("--base-input", type=Path, default=REPO / "tasks/damodaran_fcff2st/inputs/base_case.json")
    parser.add_argument("--workbook", type=Path, required=True)
    parser.add_argument("--workbook-name", default="fcff2st.xlsx", help="Public .xlsx basename specified by the task.")
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--max-steps", type=int, default=MAX_AGENT_TURNS)
    parser.add_argument("--max-run-calls", type=int, default=MAX_RUN_CALLS)
    parser.add_argument("--timeout", type=float, default=EXECUTION_TIMEOUT_SECONDS)
    parser.add_argument("--max-tokens", type=int, default=8192)
    args = parser.parse_args()
    if min(args.max_steps, args.max_run_calls, args.timeout, args.max_tokens) <= 0:
        parser.error("All execution and generation limits must be positive.")
    if Path(args.workbook_name).name != args.workbook_name or Path(args.workbook_name).suffix.lower() != ".xlsx":
        parser.error("--workbook-name must be a single .xlsx filename")

    task_prompt = args.task.read_text()
    base_input = args.base_input.read_text()
    json.loads(base_input)
    workbook = args.workbook.read_bytes()
    provider = MistralProvider(args.model, max_tokens=args.max_tokens)
    started = datetime.now(timezone.utc)
    run_dir = (args.run_dir or REPO / "runs/private" / started.strftime("mistral-%Y%m%dT%H%M%S%fZ")).resolve()
    run_dir.mkdir(parents=True, exist_ok=False)
    metadata = {
        "provider": "mistral", "requested_model": args.model,
        "started_at": started.isoformat(), "status": "running",
        "temperature": 0, "max_tokens_per_turn": args.max_tokens,
        "max_steps": args.max_steps, "max_run_calls": args.max_run_calls,
        "execution_timeout": args.timeout,
        "public_sha256": {
            "task.md": hashlib.sha256(task_prompt.encode()).hexdigest(),
            "inputs/base_case.json": hashlib.sha256(base_input.encode()).hexdigest(),
            args.workbook_name: hashlib.sha256(workbook).hexdigest(),
        },
    }
    metadata_path = run_dir / "metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2))
    print(f"Run directory: {run_dir}", flush=True)
    try:
        with tempfile.TemporaryDirectory(prefix="fcff-candidate-") as tmp:
            workspace = Path(tmp)
            (workspace / "inputs").mkdir()
            (workspace / "task.md").write_text(task_prompt)
            (workspace / "inputs/base_case.json").write_text(base_input)
            (workspace / args.workbook_name).write_bytes(workbook)
            trajectory = Agent(
                provider, workspace, run_dir, base_input,
                max_steps=args.max_steps, max_run_calls=args.max_run_calls, timeout=args.timeout,
                workbook_name=args.workbook_name,
            ).run(task_prompt)
            solution = workspace / "solution.py"
            if solution.is_symlink() or not solution.is_file():
                raise RuntimeError("The model did not leave a regular solution.py file.")
            shutil.copyfile(solution, run_dir / "solution.py")
            metadata["solution_sha256"] = hashlib.sha256((run_dir / "solution.py").read_bytes()).hexdigest()
            metadata["stop_reason"] = trajectory["stop_reason"]
            metadata["run_calls"] = trajectory["run_calls"]
            metadata["model_turns"] = len(trajectory["steps"])
            metadata["returned_models"] = sorted({
                step["response"]["model"] for step in trajectory["steps"]
            })
            metadata["usage"] = {
                key: sum(step["response"].get("usage", {}).get(key, 0) or 0 for step in trajectory["steps"])
                for key in ("prompt_tokens", "completion_tokens", "total_tokens")
            }
            metadata["status"] = "frozen"
    except Exception as exc:
        metadata["status"] = "failed"
        metadata["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        metadata["finished_at"] = datetime.now(timezone.utc).isoformat()
        metadata_path.write_text(json.dumps(metadata, indent=2))
    print(f"Frozen submission: {run_dir / 'solution.py'}", flush=True)


if __name__ == "__main__":
    main()
