"""Mistral Vibe 2.25.8 headless adapter with one benchmark MCP tool.

Install the official client with ``uv tool install mistral-vibe``. Authentication
is supplied by the caller as MISTRAL_API_KEY, an isolated VIBE_HOME/.env, or the
client's macOS Keychain entry. Account setup is ``VIBE_HOME=DIR vibe --setup``;
it requires the user to finish the official browser sign-in. VIBE_HOME isolates
configuration, not the OS Keychain. Never put credentials in the MCP arguments.

The caller must use a fresh control workspace outside the repository and strip
inherited VIBE_* config overrides before applying the returned environment.
Launch with stdin=subprocess.DEVNULL: Vibe otherwise reads stdin to EOF even
when --prompt is supplied. Streaming effect entries expose detail.toolName;
every tool event must name benchmark_run_solution.
Python candidate execution remains the MCP server's sandbox responsibility.
The installed CLI advertises Medium 3.5 using the API alias recorded below; this
is not a claim that the account has inference quota. No model fallback is used.
"""

import json
from pathlib import Path
import shutil


CLI_VERSION = "2.25.8"
MODEL_ALIASES = {"mistral-medium-3.5": "mistral-vibe-cli-latest"}
TOOL_NAME = "benchmark_run_solution"


def build_command(
    workspace: Path,
    settings_dir: Path,
    prompt: str,
    model: str,
    mcp_command: list[str],
    max_turns: int,
) -> tuple[list[str], dict[str, str]]:
    """Write private CLI settings and return argv plus environment additions.

    Streaming stdout contains completed Vibe PublicHistoryEntry JSON lines.
    Record both ``model`` and ``MODEL_ALIASES.get(model, model)`` in run metadata.
    Exact API model IDs pass through unchanged; only Vibe's advertised display
    alias is translated. Missing authentication and quota failures are terminal
    trial outcomes, not reasons to retry with a different model.
    """
    executable = shutil.which("vibe")
    if executable is None:
        raise RuntimeError("Mistral Vibe is not installed: uv tool install mistral-vibe")
    if not model or not mcp_command or max_turns < 1:
        raise ValueError("model, mcp_command and a positive max_turns are required")

    workspace = workspace.resolve()
    settings_dir = settings_dir.resolve()
    settings_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    api_model = MODEL_ALIASES.get(model, model)
    quote = json.dumps
    settings = [
        f"active_model = {quote(model)}",
        f"enabled_tools = [{quote(TOOL_NAME)}]",
        'disabled_skills = ["*"]',
        "enable_connectors = false",
        "experimental_enable_registry_skills = false",
        "include_project_context = false",
        "enable_telemetry = false",
        "enable_update_checks = false",
        "enable_auto_update = false",
        "file_watcher_for_autocomplete = false",
        "autocopy_to_clipboard = false",
        "show_greeting = false",
        "",
        "[[models]]",
        f"name = {quote(api_model)}",
        f"alias = {quote(model)}",
        'provider = "mistral"',
        "temperature = 1.0",
        'thinking = "high"',
        "",
        "[[mcp_servers]]",
        'name = "benchmark"',
        'transport = "stdio"',
        f"command = {quote(mcp_command)}",
        f"cwd = {quote(str(workspace))}",
        "startup_timeout_sec = 30",
        "tool_timeout_sec = 30",
        "",
        f"[tools.{TOOL_NAME}]",
        'permission = "always"',
        "",
    ]
    (settings_dir / "config.toml").write_text("\n".join(settings), encoding="utf-8")
    command = [
        executable,
        "--legacy-harness",
        "--workdir", str(workspace),
        "--prompt", prompt,
        "--max-turns", str(max_turns),
        "--output", "streaming",
        "--auto-approve",
        "--enabled-tools", TOOL_NAME,
    ]
    return command, {"VIBE_HOME": str(settings_dir)}
