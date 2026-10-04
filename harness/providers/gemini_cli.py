"""Launch the official Gemini CLI with only the benchmark MCP tool.

Configuration targets Gemini CLI 0.29.5. The caller must run the returned
command in a fresh, public-only control directory and pass GEMINI_API_KEY in
its host environment. Credentials are never written to these settings. Native
CLI sandboxing is deliberately disabled: run_solution's executor supplies the
candidate sandbox, while the host CLI needs network access for inference.

Reference: https://geminicli.com/docs/reference/configuration/
"""

import json
import os
import shutil
from pathlib import Path


TARGET_MODEL = "gemini-3.8-flash"


def build_command(
    workspace: Path,
    settings_dir: Path,
    prompt: str,
    model: str,
    mcp_command: list[str],
    max_turns: int,
) -> tuple[list[str], dict[str, str]]:
    """Write isolated settings and return argv plus non-secret env additions.

    The exact requested model is passed through unchanged; no alias or fallback
    is selected here. Preserve stream-json events and their per-model usage to
    detect any client-side model changes. The MCP server must expose no prompts
    or resources and only run_solution(code: string).
    """
    if not model or not mcp_command or max_turns < 1:
        raise ValueError("An explicit model, MCP command, and positive turn limit are required")
    executable = shutil.which(os.environ.get("GEMINI_CLI_BIN", "gemini"))
    if executable is None:
        raise RuntimeError("Official Gemini CLI not found; install @google/gemini-cli or set GEMINI_CLI_BIN")

    workspace = workspace.resolve()
    settings_dir = settings_dir.resolve()
    settings_dir.mkdir(parents=True, exist_ok=True)
    settings_path = settings_dir / "settings.json"
    defaults_path = settings_dir / "system-defaults.json"
    settings = {
        "general": {
            "enableAutoUpdate": False,
            "enableAutoUpdateNotification": False,
            "checkpointing": {"enabled": False},
        },
        "model": {"name": model, "maxSessionTurns": max_turns},
        "security": {"auth": {"selectedType": "gemini-api-key"}},
        # Empty JS arrays are truthy: core=[] disables every native tool in
        # Config.createToolRegistry(), including shell/file/web/memory tools.
        "tools": {"core": [], "allowed": ["run_solution"], "sandbox": False},
        "mcp": {"allowed": ["benchmark"]},
        "mcpServers": {
            "benchmark": {
                "command": mcp_command[0],
                "args": mcp_command[1:],
                "cwd": str(workspace),
                "trust": True,
                "includeTools": ["run_solution"],
            }
        },
        # Built-in subagents are registered separately from core tools.
        "agents": {
            "overrides": {
                "codebase_investigator": {"enabled": False},
                "cli_help": {"enabled": False},
            }
        },
        "experimental": {"enableAgents": False, "plan": False, "jitContext": False},
        "skills": {"enabled": False},
        "hooksConfig": {"enabled": False},
        "context": {
            "fileName": [],
            "includeDirectories": [],
            "loadMemoryFromIncludeDirectories": False,
        },
        "ide": {"enabled": False},
        "telemetry": {"enabled": False},
        "privacy": {"usageStatisticsEnabled": False},
    }
    settings_path.write_text(json.dumps(settings, indent=2) + "\n")
    defaults_path.write_text("{}\n")
    argv = [
        executable,
        "--prompt", prompt,
        "--model", model,
        "--output-format", "stream-json",
        "--extensions", "none",
        "--allowed-mcp-server-names", "benchmark",
    ]
    environment = {
        "HOME": str(settings_dir),
        "GEMINI_CLI_HOME": str(settings_dir),
        "XDG_CONFIG_HOME": str(settings_dir / ".config"),
        "GEMINI_CLI_SYSTEM_SETTINGS_PATH": str(settings_path),
        "GEMINI_CLI_SYSTEM_DEFAULTS_PATH": str(defaults_path),
        "GEMINI_SANDBOX": "false",
        "NO_BROWSER": "true",
    }
    return argv, environment
