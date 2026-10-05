from pathlib import Path
import tempfile
import unittest
from typing import Any
from unittest.mock import patch

from harness.agent import Agent
from harness.protocol import ModelResponse, ToolCall
from harness.submission import SubmissionSession, freeze_submission


class SubmissionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.workspace, self.run_dir = root / "public", root / "private"
        self.workspace.mkdir()
        self.run_dir.mkdir()
        self.session = SubmissionSession(self.workspace, self.run_dir, "{}", 4, 5)
        self.execution = patch("harness.submission.run_solution", return_value={"exit_code": 0, "stdout": "", "stderr": ""})
        self.execute = self.execution.start()
        self.addCleanup(self.execution.stop)

    def test_inspection_is_never_implicitly_submitted(self):
        result = self.session.execute("print('inspection')")
        self.assertFalse(result["submitted"])
        self.assertIsNone(result["submission"])
        with self.assertRaisesRegex(RuntimeError, "No explicit submission"):
            freeze_submission(self.run_dir)
        self.assertFalse((self.run_dir / "solution.py").exists())

    def test_submit_then_inspect_and_mutate_preserves_exact_source(self):
        source = "print('submitted')\n"
        self.session.execute(source, submit=True)
        (self.workspace / "solution.py").write_text("mutated")
        result = self.session.execute("print('inspection')")
        self.assertEqual(result["submission"]["run_call"], 1)
        metadata = freeze_submission(self.run_dir)
        self.assertEqual(metadata["submission_run_call"], 1)
        self.assertEqual((self.run_dir / "solution.py").read_text(), source)

    def test_last_explicit_submission_survives_errors_restart_and_budget(self):
        self.session.execute("first", submit=True)
        self.execute.return_value = {"exit_code": 1, "stdout": "", "stderr": "failure"}
        self.session.execute("second", submit=True)
        restarted = SubmissionSession(self.workspace, self.run_dir, "changed", 2, 5)
        self.assertEqual(restarted.base_input, "{}")
        result = restarted.execute("over budget", submit=True)
        self.assertIn("error", result)
        metadata = freeze_submission(self.run_dir)
        self.assertEqual(metadata["run_calls"], 2)
        self.assertEqual((self.run_dir / "solution.py").read_text(), "second")

    def test_invalid_submit_does_not_execute_or_consume_budget(self):
        invalid_values: tuple[Any, ...] = ("false", "true", 1, None)
        for invalid in invalid_values:
            self.assertIn("error", self.session.execute("print(1)", submit=invalid))
        self.execute.assert_not_called()
        self.assertFalse(self.session.state_path.exists())

    def test_run_directory_cannot_be_public(self):
        for path in (self.workspace, self.workspace / "nested", self.workspace.parent):
            path.mkdir(exist_ok=True)
            with self.assertRaisesRegex(ValueError, "disjoint"):
                SubmissionSession(self.workspace, path, "{}", 1, 5)

    def test_private_snapshots_and_workspace_cannot_overlap_readable_runtime(self):
        trusted = self.workspace.parent / "trusted-runtime"
        nested = trusted / "runs"
        nested.mkdir(parents=True)
        with patch("harness.executor._runtime_paths", return_value=({trusted}, set(), set())):
            with self.assertRaisesRegex(ValueError, "trusted runtime"):
                SubmissionSession(self.workspace, nested, "{}", 1, 5)
            with self.assertRaisesRegex(ValueError, "trusted runtime"):
                SubmissionSession(nested, self.run_dir, "{}", 1, 5)
        self.assertFalse((nested / "execution-state.lock").exists())

    def test_tampered_host_snapshot_cannot_be_frozen(self):
        self.session.execute("submitted", submit=True)
        (self.run_dir / "step-01.py").write_text("tampered")
        with self.assertRaisesRegex(RuntimeError, "hash mismatch"):
            freeze_submission(self.run_dir)

    def test_api_agent_uses_same_explicit_submission_state(self):
        calls = [ToolCall("run_solution", {"code": "submitted", "submit": True}, "1"),
                 ToolCall("run_solution", {"code": "inspection"}, "2")]
        response = ModelResponse(text="", tool_calls=calls, raw={"choices": [{"finish_reason": "tool_calls"}]})

        class Provider:
            def generate(self, messages):
                return response

            def assistant_message(self, response):
                return {"role": "assistant", "content": ""}

        trajectory = Agent(Provider(), self.workspace, self.run_dir, "{}", max_steps=1, max_run_calls=2).run("task")
        self.assertEqual(trajectory["run_calls"], 2)
        freeze_submission(self.run_dir)
        self.assertEqual((self.run_dir / "solution.py").read_text(), "submitted")


if __name__ == "__main__":
    unittest.main()
