import json
from pathlib import Path
import sys
import tempfile
import unittest

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


if __name__ == "__main__":
    unittest.main()
