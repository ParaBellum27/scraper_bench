"""Local synthetic-canary probe; no provider requests or actual secrets."""
import json
from pathlib import Path
import sys
import tempfile

from harness.executor import run_solution

with tempfile.TemporaryDirectory(dir="/private/tmp") as root, tempfile.NamedTemporaryFile(prefix="audit-canary-", dir=sys.prefix) as canary:
    canary.write(b"synthetic-canary")
    canary.flush()
    workspace = Path(root) / "public"
    workspace.mkdir()
    solution = workspace / "solution.py"
    solution.write_text(
        "from pathlib import Path\n"
        f"try: print(Path({canary.name!r}).read_text())\n"
        "except PermissionError: print('denied')\n"
        "Path('solution.py').write_text('debug-mutated')\n"
    )
    result = run_solution(str(solution))
    print(json.dumps({"runtime_prefix_read": result, "workspace_mutated": solution.read_text() == "debug-mutated"}, indent=2))
