import json
from pathlib import Path
import tempfile
import unittest

from harness.run_terminal import audit_events


class TerminalAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="fcff-terminal-audit-")
        self.addCleanup(self.temp.cleanup)
        self.run_dir = Path(self.temp.name)
        self.events = self.run_dir / "cli-events.jsonl"

    def test_native_shell_effect_invalidates_one_tool_trial(self):
        self.events.write_text(json.dumps({
            "type": "effect",
            "detail": {"kind": "shell", "toolName": "bash", "input": {"command": "pwd"}},
        }) + "\n")
        with self.assertRaisesRegex(RuntimeError, "Unexpected native tools"):
            audit_events(self.events, "mistral", "mistral-medium-3.5")

    def test_per_turn_model_change_invalidates_requested_model_trial(self):
        self.events.write_text(json.dumps({"type": "init", "model": "gemini-3.8-flash"}) + "\n")
        sessions = self.run_dir / "native-sessions"
        sessions.mkdir()
        (sessions / "session.json").write_text(json.dumps({
            "messages": [{"type": "gemini", "model": "different-model", "content": "answer"}],
        }))
        with self.assertRaisesRegex(RuntimeError, "changed the requested model"):
            audit_events(self.events, "gemini", "gemini-3.8-flash")


if __name__ == "__main__":
    unittest.main()
