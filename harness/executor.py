"""Fail-closed macOS execution of an untrusted, public-workspace solution."""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
import selectors
import signal
import subprocess
import sys
import time


_SANDBOX = Path("/usr/bin/sandbox-exec")
_REPO = Path(__file__).resolve().parents[1]
_OUTPUT_LIMIT = 64 * 1024  # Per stream; terminate rather than accumulate or spool.


def _python_binary() -> Path:
    # Homebrew's bin/python launcher spawns this interpreter. Execute it directly
    # so candidate process-fork stays denied, retaining the venv via its launcher.
    framework_binary = Path(sys.base_prefix) / "Resources/Python.app/Contents/MacOS/Python"
    return framework_binary.resolve() if framework_binary.is_file() else Path(sys.executable).resolve()


def _profile(workspace: Path) -> str:
    # Resolve Homebrew symlinks too: sandbox path filters see canonical paths.
    runtime = {
        Path(sys.prefix), Path(sys.base_prefix),
        Path("/System/Library"), Path("/usr/lib"),
        Path("/Library/Apple/System/Library"),
    }
    # Optional stdlib extensions depend on these Homebrew runtime libraries.
    for name in ("openssl@3", "xz", "mpdecimal", "sqlite", "readline", "expat", "libffi"):
        library = Path("/opt/homebrew/opt") / name / "lib"
        if library.is_dir():
            runtime.add(library)
    runtime |= {path.resolve() for path in runtime}
    executable = Path(sys.executable)
    launchers = {executable, executable.resolve(), _python_binary()}
    link = executable
    while link.is_symlink():
        # Kernel path traversal checks each link, not just the final target.
        launchers.add(link.parent.resolve() / link.name)
        link = Path(os.path.abspath(link.parent / link.readlink()))
        launchers.add(link)
    metadata = {Path("/")} | launchers
    for path in runtime | {workspace} | launchers:
        metadata.update(path.parents)

    def filters(kind: str, paths: set[Path]) -> str:
        return " ".join(f"({kind} {json.dumps(str(path))})" for path in sorted(paths))

    readable = runtime | {workspace}
    return "\n".join([
        "(version 1)",
        "(deny default)",
        "(deny network*)",
        # No fork/posix_spawn, Mach services, process inspection, or other home reads.
        "(deny process-fork)",
        f"(allow process-exec {filters('literal', launchers)})",
        f"(allow file-read* {filters('subpath', readable)})",
        f"(allow file-read-metadata {filters('literal', metadata)})",
        # dyld opens the root directory during startup; no descendant reads.
        '(allow file-read-data (literal "/"))',
        f"(allow file-map-executable {filters('subpath', runtime)})",
        '(allow file-read* (literal "/dev/null") (literal "/dev/random") (literal "/dev/urandom"))',
        f"(allow file-write* {filters('subpath', {workspace})})",
        "(allow sysctl-read)",
        '(deny file-read* (regex #"/[.]env($|/)"))',
    ])


def _kill_group(proc: subprocess.Popen) -> None:
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def _capture(proc: subprocess.Popen, stdin: str, timeout: float) -> dict:
    assert proc.stdin is not None and proc.stdout is not None and proc.stderr is not None
    buffers = {"stdout": bytearray(), "stderr": bytearray()}
    pending = memoryview(stdin.encode("utf-8"))
    deadline = time.monotonic() + timeout
    failure = None
    with selectors.DefaultSelector() as selector:
        for stream, name in ((proc.stdout, "stdout"), (proc.stderr, "stderr")):
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, selectors.EVENT_READ, (stream, name))
        if pending:
            os.set_blocking(proc.stdin.fileno(), False)
            selector.register(proc.stdin, selectors.EVENT_WRITE, (proc.stdin, "stdin"))
        else:
            proc.stdin.close()

        while selector.get_map() and failure is None:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                failure = (124, f"Execution timed out after {timeout:g}s")
                break
            for key, _ in selector.select(remaining):
                stream, name = key.data
                if name == "stdin":
                    try:
                        count = os.write(stream.fileno(), pending[:65536])
                        pending = pending[count:]
                    except BrokenPipeError:
                        pending = pending[:0]
                    if not pending:
                        selector.unregister(stream)
                        stream.close()
                    continue
                data = os.read(stream.fileno(), 8192)
                if not data:
                    selector.unregister(stream)
                    stream.close()
                    continue
                available = _OUTPUT_LIMIT - len(buffers[name])
                buffers[name].extend(data[:available])
                if len(data) > available:
                    failure = (125, f"Execution exceeded {_OUTPUT_LIMIT}-byte {name} limit")
                    break

        if failure is None:
            try:
                proc.wait(timeout=max(0, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                failure = (124, f"Execution timed out after {timeout:g}s")
    result = {
        "exit_code": failure[0] if failure else proc.returncode,
        "stdout": buffers["stdout"].decode("utf-8", errors="replace"),
        "stderr": buffers["stderr"].decode("utf-8", errors="replace"),
    }
    if failure:
        result["stderr"] = result["stderr"][:_OUTPUT_LIMIT - 200] + "\n" + failure[1]
    return result


def run_solution(solution_path: str, timeout: int | float = 10, stdin: str = "") -> dict:
    """Run with clean env, bounded output, and workspace-only filesystem writes.

    The caller must supply a public-only workspace outside this repository.
    Exit 124 means timeout; 125 means setup/sandbox or output-limit failure.
    """
    proc = None
    try:
        if sys.platform != "darwin" or not _SANDBOX.is_file():
            raise RuntimeError("macOS sandbox-exec is required; refusing unsandboxed execution")
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("timeout must be finite and positive")
        path = Path(solution_path).resolve(strict=True)
        workspace = path.parent
        if not path.is_file():
            raise ValueError("solution must be a regular file")
        # Reject ancestors as well: allowing /tmp or a home root would expose
        # unrelated files, and allowing a repo ancestor would expose the grader.
        if workspace == _REPO or _REPO in workspace.parents or workspace in _REPO.parents:
            raise ValueError("solution workspace must be outside the repository")
        if workspace in {Path("/tmp").resolve(), Path("/private/tmp"), Path("/var/tmp").resolve()}:
            raise ValueError("solution must be inside a dedicated workspace, not a shared temp root")
        environment = {
            "PATH": str(Path(sys.executable).parent),
            "HOME": str(workspace),
            "TMPDIR": str(workspace),
            "LANG": "en_US.UTF-8",
            "LC_ALL": "en_US.UTF-8",
            "__PYVENV_LAUNCHER__": sys.executable,
        }
        proc = subprocess.Popen(
            [str(_SANDBOX), "-p", _profile(workspace), str(_python_binary()), "-I", "-B", "-u", str(path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=workspace,
            env=environment,
            start_new_session=True,
            close_fds=True,
        )
        return _capture(proc, stdin, float(timeout))
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return {"exit_code": 125, "stdout": "", "stderr": f"Sandbox execution failed: {exc}"}
    finally:
        if proc is not None:
            _kill_group(proc)
            proc.wait()
            for stream in (proc.stdin, proc.stdout, proc.stderr):
                if stream is not None:
                    stream.close()
