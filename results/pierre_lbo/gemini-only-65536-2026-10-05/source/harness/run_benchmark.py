"""Pinned direct-API campaign. Default is a local check; execution is opt-in."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import time

from harness.agent import Agent
from harness.direct_campaign import (
    POLICY_PATH, PRIVATE_RELATIVE, available_trial_claim, claim_trial, digest, load_policy, local_key,
    private_json, public_bundle, readiness,
)
from harness.executor import run_solution, validate_runtime_separation
from harness.providers.gemini import GeminiProvider
from harness.providers.groq import GroqProvider
from harness.providers.mistral import MistralProvider
from harness.request_guard import GuardError, GuardedTransport
from harness.submission import freeze_submission


REPO = Path(__file__).resolve().parent.parent
PROVIDERS = {"groq": GroqProvider, "gemini": GeminiProvider, "mistral": MistralProvider}


def run_trial(root: Path, config: dict, provider_name: str, *, access_only: bool) -> tuple[int, Path]:
    """Host integration entrypoint; CLI validates release before calling it."""
    start = time.monotonic()
    deadline = start + config["wall_timeout_seconds"]
    target = config["targets"][provider_name]
    key = local_key(root, target["credential_env"])
    files = public_bundle(root, config)
    campaign_dir = root / PRIVATE_RELATIVE
    campaign_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    started = datetime.now(timezone.utc)
    run_id = started.strftime(f"{provider_name}-%Y%m%dT%H%M%S%fZ")
    run_dir = campaign_dir / run_id
    run_dir.mkdir(mode=0o700)
    validate_runtime_separation(run_dir)
    metadata = {
        "provider": provider_name, "requested_model": target["model"],
        "transport": "native-generateContent" if provider_name == "gemini" else "chat-completions",
        "started_at": started.isoformat(), "status": "preparing", "candidate_started": False,
        "access_only": access_only, "score": None,
        "requested_temperature": "provider_default", "requested_thinking": "provider_default",
        "effective_temperature": None, "effective_thinking": None,
        "unexposed_defaults": "unavailable; no values inferred",
        "limits": {k: config[k] for k in ("max_steps", "max_run_calls", "execution_timeout_seconds",
                   "wall_timeout_seconds", "max_output_tokens", "access_check_output_tokens")},
        "public_sha256": {name: digest(data) for name, data in files.items()},
        "policy_sha256": digest(POLICY_PATH.read_bytes()),
        "request_policy": target,
        "credential_source": "local .env only; no exported-key fallback",
    }
    metadata_path = run_dir / "metadata.json"
    private_json(metadata_path, metadata)
    code = 1
    try:
        with GuardedTransport(target, key, campaign_dir / "ledger.json", deadline, run_id) as transport:
            try:
                trial_limit = config["exploratory_trials_per_provider"][provider_name]
                if not access_only:
                    try:
                        available_trial_claim(campaign_dir, provider_name, trial_limit)
                    except FileExistsError:
                        raise GuardError("budget", "All authorized exploratory trials were already claimed") from None
                with tempfile.TemporaryDirectory(prefix="pierre-candidate-", dir="/private/tmp") as directory:
                    workspace = Path(directory)
                    for name, data in files.items():
                        path = workspace / name
                        path.parent.mkdir(parents=True, exist_ok=True)
                        path.write_bytes(data)
                    # Prove local execution/workbook access before spending on a
                    # provider check. This code never selects a submission.
                    smoke_path = workspace / "preflight.py"
                    smoke_path.write_text(
                        "import json,openpyxl\n"
                        "w=openpyxl.load_workbook('pierre_lbo_one.xlsx',read_only=True,data_only=True)\n"
                        "print(json.dumps(w.sheetnames))\nw.close()\n"
                    )
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise GuardError("deadline", "Whole-run deadline reached before local preflight")
                    smoke = run_solution(str(smoke_path), timeout=min(config["execution_timeout_seconds"], remaining))
                    smoke_path.unlink()
                    if smoke["exit_code"] or json.loads(smoke["stdout"]) != ["Inputs", "Scenarios", "Forecast", "Debt", "Returns"]:
                        raise GuardError("infrastructure", "Public workbook sandbox preflight failed")
                    metadata["local_preflight"] = smoke
                    probe = PROVIDERS[provider_name](target["model"], config["access_check_output_tokens"], transport)
                    response = probe.generate([{"role": "user", "content": "Reply with READY only. Do not call any tool."}])
                    private_json(run_dir / "access-check.json", response.raw)
                    if response.tool_calls or response.text.strip() != "READY":
                        raise GuardError("protocol", "Access check did not return the requested READY response")
                    metadata["access_returned_model"] = response.raw.get("model")
                    metadata["status"] = "access_verified"
                    private_json(metadata_path, metadata)
                    if not access_only:
                        claim_trial(campaign_dir, provider_name, run_id, trial_limit)
                        metadata["candidate_started"] = True
                        metadata["status"] = "running"
                        private_json(metadata_path, metadata)
                        provider = PROVIDERS[provider_name](target["model"], config["max_output_tokens"], transport)
                        trajectory = Agent(
                            provider, workspace, run_dir, files["inputs/base_case.json"].decode(),
                            max_steps=config["max_steps"], max_run_calls=config["max_run_calls"],
                            timeout=config["execution_timeout_seconds"], workbook_name="pierre_lbo_one.xlsx",
                            deadline=deadline,
                        ).run(files["task.md"].decode())
                        metadata["stop_reason"] = trajectory["stop_reason"]
                        metadata["model_turns"] = len(trajectory["steps"])
                        metadata["returned_models"] = sorted({
                            step["response"]["model"] for step in trajectory["steps"]
                            if isinstance(step["response"].get("model"), str)
                        })
                        state_path = run_dir / "execution-state.json"
                        state = json.loads(state_path.read_text()) if state_path.exists() else {}
                        if not state.get("submission"):
                            metadata["status"] = "ungraded_no_submission"
                            metadata["error_category"] = "candidate_submission"
                        else:
                            metadata.update(freeze_submission(run_dir))
                            metadata["status"] = "frozen"
                            code = 0
                    else:
                        code = 0
            finally:
                metadata["accounting"] = transport.summary()
    except Exception as exc:
        metadata["status"] = "candidate_failed" if metadata["candidate_started"] else "access_failed"
        metadata["error_category"] = getattr(exc, "category", "infrastructure")
        metadata["error"] = f"{type(exc).__name__}: {exc}".replace(key, "[redacted]")
        raw = getattr(exc, "raw", None)
        if isinstance(raw, dict):
            # Redact even an unexpected provider echo before retaining evidence.
            safe = json.loads(json.dumps(raw, allow_nan=False).replace(key, "[redacted]"))
            private_json(run_dir / "provider-error.json", safe)
    finally:
        metadata["finished_at"] = datetime.now(timezone.utc).isoformat()
        metadata["elapsed_seconds"] = time.monotonic() - start
        private_json(metadata_path, metadata)
    return code, run_dir


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", choices=sorted(PROVIDERS), required=True)
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--check", action="store_true", help="Local checks only; the default. Never sends a request.")
    action.add_argument("--access-check", action="store_true", help="One bounded model-access probe; no candidate trial.")
    action.add_argument("--execute", action="store_true", help="Access probe then one explicitly authorized candidate trial.")
    args = parser.parse_args()
    config = load_policy()
    report = readiness(REPO, config, args.provider, execute=args.execute)
    if not args.execute and not args.access_check:
        print(json.dumps(report, indent=2))
        return 0 if report["ready"] else 2
    if not report["ready"]:
        print(json.dumps(report, indent=2))
        return 2
    code, directory = run_trial(REPO, config, args.provider, access_only=not args.execute)
    print(json.dumps({"run_directory": str(directory), "exit_code": code}, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
