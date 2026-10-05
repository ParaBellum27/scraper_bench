"""Pinned Pierre campaign configuration and host-only release decisions."""

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile

from dotenv import dotenv_values


POLICY_PATH = Path(__file__).with_name("direct_policy.json")
PRIVATE_RELATIVE = Path("runs/private/pierre_lbo/direct-api")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_policy() -> dict:
    return json.loads(POLICY_PATH.read_text())

def select_condition(config: dict, name: str | None = None) -> dict:
    """Copy the complete policy, applying only an explicitly named run-call limit."""
    profiles = config.get("comparison_conditions", {})
    if not isinstance(profiles, dict):
        raise ValueError("Comparison conditions must be an object")
    for condition, overrides in profiles.items():
        if condition not in {"calls12", "calls24"}:
            raise ValueError("Unsupported comparison condition")
        if not isinstance(overrides, dict) or set(overrides) != {"max_run_calls"}:
            raise ValueError("Conditions may override only max_run_calls")
        value = overrides["max_run_calls"]
        if type(value) is not int or value <= 0:
            raise ValueError("Condition max_run_calls must be a positive integer")
    if name is not None and (not isinstance(name, str) or name not in profiles):
        raise ValueError("Unknown comparison condition")
    effective = deepcopy(config)
    effective.pop("selected_condition", None)
    if name is not None:
        effective.update(profiles[name])
        effective["selected_condition"] = name
    return effective


def effective_config_sha256(config: dict) -> str:
    """Bind all effective settings using a canonical, finite JSON representation."""
    return digest(json.dumps(config, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=False, allow_nan=False).encode("utf-8"))



def local_key(root: Path, name: str) -> str:
    # Never interpolate ${EXPORTED_KEY}, prefer an exported key, or mutate the
    # environment inherited by unrelated code. The selected .env is authoritative.
    value = dotenv_values(root / ".env", interpolate=False).get(name)
    if not isinstance(value, str) or not value or any(c.isspace() for c in value) or "${" in value:
        raise ValueError(f"Missing or invalid local .env credential: {name}")
    return value


def private_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(value, stream, indent=2, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        Path(temporary).unlink(missing_ok=True)


def public_bundle(root: Path, config: dict) -> dict[str, bytes]:
    metadata_path = root / config["public_metadata"]
    metadata = json.loads(metadata_path.read_text())
    files = {}
    for name, expected in metadata["public_artifact_sha256"].items():
        if Path(name).is_absolute() or ".." in Path(name).parts:
            raise ValueError("Invalid public artifact path")
        data = (metadata_path.parent / name).read_bytes()
        if digest(data) != expected:
            raise ValueError(f"Frozen public artifact changed: {name}")
        files[name] = data
    if set(files) != {"task.md", "pierre_lbo_one.xlsx", "inputs/base_case.json"}:
        raise ValueError("Unexpected Pierre public bundle")
    return files


def readiness(root: Path, config: dict, provider: str, *, execute: bool = False) -> dict:
    target = config["targets"][provider]
    blockers = []
    condition = config.get("selected_condition")
    effective_hash = effective_config_sha256(config)
    try:
        validated = select_condition(config, condition)
        if validated != config:
            blockers.append("Effective condition configuration does not match its profile")
    except ValueError as exc:
        blockers.append(str(exc))
    now = datetime.now(timezone.utc)
    if now.date().isoformat() >= config["price_valid_before"]:
        blockers.append("Pricing/allowance verification expired; reverify before any request")
    try:
        key = local_key(root, target["credential_env"])
    except ValueError as exc:
        blockers.append(str(exc))
        key = None
    try:
        files = public_bundle(root, config)
        hashes = {name: digest(data) for name, data in files.items()}
    except (OSError, ValueError, KeyError) as exc:
        blockers.append(f"Public bundle verification failed: {type(exc).__name__}")
        hashes = {}
    release_path = root / PRIVATE_RELATIVE / "release.json"
    if release_path.exists():
        try:
            release = json.loads(release_path.read_text())
            if not isinstance(release, dict):
                raise ValueError
        except (OSError, ValueError):
            blockers.append("Invalid private release record")
            release = {}
    else:
        release = {}
    if release.get("policy_sha256") != digest(POLICY_PATH.read_bytes()):
        blockers.append("Release record is missing or not bound to current policy")
    if release.get("access_checks_authorized") is not True:
        blockers.append("Access checks not authorized")
    authorized_providers = release.get("candidate_providers", [])
    candidate_authorized = (
        release.get("candidate_trials_authorized") is True
        and isinstance(authorized_providers, list) and provider in authorized_providers
    )
    condition_authorized = True
    if "candidate_conditions" in release or condition is not None:
        authorized_conditions = release.get("candidate_conditions")
        condition_authorized = (
            condition is not None and isinstance(authorized_conditions, list)
            and condition in authorized_conditions
        )
        if execute and not condition_authorized:
            blockers.append("Candidate condition not authorized")
    authorized_hashes = release.get("authorized_condition_sha256", {})
    if condition is not None:
        if not isinstance(authorized_hashes, dict) or authorized_hashes.get(condition) != effective_hash:
            blockers.append("Selected condition is not bound to the effective configuration")
            condition_authorized = False
    candidate_authorized = candidate_authorized and condition_authorized
    if execute and not candidate_authorized:
        blockers.append("Candidate trials not authorized")
    account = release.get("accounts", {}).get(provider, {})
    if account.get("verified") is not True:
        blockers.append("Account entitlement not confirmed")
    if key and account.get("credential_sha256") != digest(key.encode()):
        blockers.append("Current local key differs from confirmed account key")
    if account.get("valid_before", "") <= now.isoformat():
        blockers.append("Account/allowance confirmation expired")
    if provider == "groq" and account.get("free_only_no_paid_billing") is not True:
        blockers.append("Groq free-only billing not confirmed")
    if provider == "gemini" and account.get("project") != "Default Gemini Project":
        blockers.append("Gemini key-to-project association not confirmed")
    if provider == "mistral" and (account.get("reserved_included_usd") != target["spend_cap_usd"] or account.get("no_competing_usage") is not True):
        blockers.append("Mistral included allowance not reserved exclusively")
    return {"provider": provider, "model": target["model"], "ready": not blockers,
            "blockers": blockers, "public_sha256": hashes,
            "credential_source": "local .env only; exported credentials ignored",
            "max_output_tokens": config["max_output_tokens"],
            "candidate_trials_authorized": candidate_authorized,
            "selected_condition": condition, "effective_config_sha256": effective_hash,
            "authorized_condition_sha256": authorized_hashes}


def available_trial_claim(campaign_dir: Path, provider: str, limit: int) -> Path:
    """Find an unclaimed authorized slot while the campaign lock is held."""
    if type(limit) is not int or limit < 1:
        raise ValueError("Trial allowance must be a positive integer")
    for number in range(1, limit + 1):
        suffix = "" if number == 1 else f"-{number:02d}"
        path = campaign_dir / f"{provider}-trial-claim{suffix}.json"
        if not path.exists():
            return path
    raise FileExistsError("All authorized trial slots are already claimed")


def claim_trial(campaign_dir: Path, provider: str, run_id: str, limit: int) -> None:
    """Call only while the shared GuardedTransport campaign lock is held.

    Exclusive claim files survive crashes. Failed/unfinished trials still count;
    neither a new run directory nor a new process silently resets the allowance.
    """
    claim = available_trial_claim(campaign_dir, provider, limit)
    with claim.open("x") as stream:
        json.dump({"provider": provider, "run_id": run_id,
                   "claimed_at": datetime.now(timezone.utc).isoformat()}, stream)
        stream.flush()
        os.fsync(stream.fileno())
    directory = os.open(campaign_dir, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)
