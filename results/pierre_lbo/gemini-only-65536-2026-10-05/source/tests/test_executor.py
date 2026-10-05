import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from harness.executor import run_solution
from evaluator.run_grader import run_submission


@unittest.skipUnless(sys.platform == "darwin", "requires macOS sandbox-exec")
class ExecutorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="fcff-boundary-", dir="/private/tmp")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.workspace = self.root / "public"
        self.workspace.mkdir()
        self.solution = self.workspace / "solution.py"

    def execute(self, source, stdin="", timeout=5):
        self.solution.write_text(source)
        return run_solution(str(self.solution), timeout=timeout, stdin=stdin)

    def test_public_stdin_scratch_and_private_boundaries(self):
        private = self.root / "private.txt"
        private.write_text("private sentinel")
        (self.workspace / "escape").symlink_to(private)
        result = self.execute(
            "import json, os, socket, sys\n"
            "from pathlib import Path\n"
            "out = {'input': json.load(sys.stdin)}\n"
            "Path('scratch').write_text('public scratch')\n"
            "out['scratch'] = Path('scratch').read_text()\n"
            "out['api_key_present'] = any(k.endswith('_API_KEY') for k in os.environ)\n"
            f"for label, path in [('private', {str(private)!r}), ('symlink', 'escape')]:\n"
            "    try:\n"
            "        Path(path).read_text(); out[label] = 'readable'\n"
            "    except PermissionError:\n"
            "        out[label] = 'denied'\n"
            "try:\n"
            "    socket.socket().connect(('127.0.0.1', 9)); out['network'] = 'connected'\n"
            "except PermissionError:\n"
            "    out['network'] = 'denied'\n"
            "print(json.dumps(out))\n",
            stdin='{"value":42}',
        )
        self.assertEqual(result["exit_code"], 0, result)
        self.assertEqual(json.loads(result["stdout"]), {
            "input": {"value": 42}, "scratch": "public scratch",
            "api_key_present": False, "private": "denied", "symlink": "denied", "network": "denied",
        })

    def test_hung_and_noisy_candidates_are_stopped(self):
        hung = self.execute("while True: pass\n", timeout=0.3)
        self.assertEqual(hung["exit_code"], 124)
        noisy = self.execute("print('x' * 100000)\n")
        self.assertEqual(noisy["exit_code"], 125)
        self.assertLessEqual(len(noisy["stdout"].encode()), 65536)

    def test_grading_hides_workbook_and_resets_case_state(self):
        (self.workspace / "fcff2st.xlsx").write_bytes(b"not for grading")
        self.solution.write_text(
            "import json, sys\n"
            "from pathlib import Path\n"
            "out = {'input': json.load(sys.stdin), 'files': sorted(p.name for p in Path('.').iterdir())}\n"
            "Path('scratch').write_text('must not survive between cases')\n"
            "print(json.dumps(out))\n"
        )
        for value in (3, 7):
            output, error = run_submission(self.solution, {"value": value}, timeout=5)
            self.assertIsNone(error)
            self.assertEqual(output, {"input": {"value": value}, "files": ["solution.py"]})

    def test_grading_rejects_nonfinite_json_even_in_extra_fields(self):
        for token in ("NaN", "Infinity", "-Infinity", "1e999"):
            with self.subTest(token=token):
                text = '{"scoreable": 1, "extra": {"nested": [' + token + ']}}'
                self.solution.write_text(f"print({text!r})\n")
                output, error = run_submission(self.solution, {}, timeout=5)
                self.assertIsNone(output)
                assert error is not None
                self.assertIn("invalid JSON", error)

    def test_runtime_prefix_canary_is_not_readable(self):
        # A synthetic prefix located at the repo root must not grant repo reads.
        with patch("harness.executor.sys.prefix", str(Path(__file__).resolve().parents[1])):
            result = self.execute(
                "from pathlib import Path\n"
                f"try: Path({str(Path(__file__).resolve())!r}).read_bytes(); print('readable')\n"
                "except PermissionError: print('denied')\n"
            )
        self.assertEqual(result["exit_code"], 0, result)
        self.assertEqual(result["stdout"].strip(), "denied")

    def test_environment_descriptors_imports_fork_and_subprocess_are_isolated(self):
        canary = self.root / "canary.py"
        canary.write_text("SENTINEL = 'synthetic-canary'\n")
        credential = self.workspace / ".env"
        credential.write_text("AUDIT_TOKEN=synthetic-canary\n")
        with canary.open("rb") as inherited:
            os.set_inheritable(inherited.fileno(), True)
            with patch.dict(os.environ, {"AUDIT_TOKEN": "synthetic-canary", "PYTHONPATH": str(self.root)}):
                result = self.execute(
                    "import importlib.util, json, os, subprocess, sys\n"
                    "out = {'env': 'AUDIT_TOKEN' not in os.environ, 'pythonpath': 'PYTHONPATH' not in os.environ}\n"
                    f"try: os.read({inherited.fileno()}, 100); out['fd'] = False\n"
                    "except OSError: out['fd'] = True\n"
                    "def denied(label, action):\n"
                    "    try: action(); out[label] = False\n"
                    "    except PermissionError: out[label] = True\n"
                    "def import_private():\n"
                    f"    spec = importlib.util.spec_from_file_location('canary', {str(canary)!r})\n"
                    "    spec.loader.exec_module(importlib.util.module_from_spec(spec))\n"
                    "denied('import', import_private)\n"
                    "denied('dotenv', lambda: open('.env').read())\n"
                    "denied('fork', os.fork)\n"
                    "denied('subprocess', lambda: subprocess.run([sys.executable, '-c', 'print(1)']))\n"
                    "print(json.dumps(out))\n"
                )
        self.assertEqual(result["exit_code"], 0, result)
        self.assertEqual(json.loads(result["stdout"]), dict.fromkeys(("env", "pythonpath", "fd", "import", "dotenv", "fork", "subprocess"), True))


class FailClosedTests(unittest.TestCase):
    def test_unsupported_platform_is_never_executed(self):
        with patch("harness.executor.sys.platform", "linux"), patch("harness.executor.subprocess.Popen") as launch:
            result = run_solution("/does/not/matter.py")
        self.assertEqual(result["exit_code"], 125)
        launch.assert_not_called()

    def test_arbitrary_stdlib_siblings_are_not_runtime_components(self):
        from harness.executor import _runtime_paths

        with tempfile.TemporaryDirectory() as root:
            stdlib = Path(root)
            (stdlib / "json").mkdir()
            (stdlib / "audit-injected").mkdir()
            (stdlib / "audit-credential.py").write_text("synthetic-canary")
            (stdlib / "lib-dynload").mkdir()
            (stdlib / "lib-dynload/audit-injected.so").write_bytes(b"synthetic-canary")
            with patch("harness.executor.sysconfig.get_path", return_value=str(stdlib)):
                trees, literals, _ = _runtime_paths()
            self.assertIn((stdlib / "json").resolve(), trees)
            self.assertNotIn((stdlib / "audit-injected").resolve(), trees)
            self.assertNotIn((stdlib / "audit-credential.py").resolve(), literals)
            self.assertNotIn((stdlib / "lib-dynload/audit-injected.so").resolve(), literals)


if __name__ == "__main__":
    unittest.main()
