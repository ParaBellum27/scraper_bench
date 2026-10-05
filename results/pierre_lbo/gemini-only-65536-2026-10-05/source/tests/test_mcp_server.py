import contextlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from harness.submission import freeze_submission


@unittest.skipUnless(sys.platform == "darwin", "requires macOS sandbox-exec")
class McpServerTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="fcff-mcp-test-", dir="/private/tmp")
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.workspace = root / "public"
        (self.workspace / "inputs").mkdir(parents=True)
        (self.workspace / "inputs/base_case.json").write_text('{"value":42}')
        self.run_dir = root / "private"
        self.run_dir.mkdir()
        self.server_path = Path(__file__).resolve().parents[1] / "harness/mcp_server.py"

    @contextlib.asynccontextmanager
    async def connect(self, limit):
        params = StdioServerParameters(
            command=sys.executable,
            args=[str(self.server_path), "--workspace", str(self.workspace),
                  "--run-dir", str(self.run_dir), "--max-run-calls", str(limit)],
        )
        async with stdio_client(params) as streams:
            async with ClientSession(*streams) as session:
                await session.initialize()
                yield session

    async def execute(self, session, source, submit=False):
        response = await session.call_tool("run_solution", {"code": source, "submit": submit})
        self.assertFalse(response.isError, response)
        return json.loads(response.content[0].text)

    async def test_server_restart_does_not_reset_execution_budget(self):
        async with self.connect(limit=1) as session:
            result = await self.execute(session, "print(42)")
            self.assertEqual(result["exit_code"], 0)
            self.assertEqual(result["stdout"].strip(), "42")
        async with self.connect(limit=1) as session:
            result = await self.execute(session, "open('extra-execution', 'w').write('ran')")
            self.assertIn("error", result)
            self.assertEqual(result["remaining"], 0)
        self.assertFalse((self.workspace / "extra-execution").exists())

    async def test_restart_preserves_original_stdin_after_candidate_modification(self):
        async with self.connect(limit=2) as session:
            result = await self.execute(session, "open('inputs/base_case.json', 'w').write('{}')")
            self.assertEqual(result["exit_code"], 0, result)
        async with self.connect(limit=2) as session:
            result = await self.execute(session, "import sys; print(sys.stdin.read())")
            self.assertEqual(result["exit_code"], 0, result)
            self.assertEqual(json.loads(result["stdout"]), {"value": 42})

    async def test_explicit_submission_survives_self_mutation_and_later_inspection(self):
        source = "from pathlib import Path\nPath('solution.py').write_text('mutated')\nprint(42)\n"
        async with self.connect(limit=3) as session:
            tools = await session.list_tools()
            self.assertEqual([tool.name for tool in tools.tools], ["run_solution"])
            schema = tools.tools[0].inputSchema
            self.assertEqual(schema["properties"]["submit"]["default"], False)
            result = await self.execute(session, source, submit=True)
            self.assertEqual(result["exit_code"], 0, result)
            self.assertTrue(result["submitted"])
        async with self.connect(limit=3) as session:
            snapshot = self.run_dir / "step-01.py"
            inspection = (
                "from pathlib import Path\n"
                f"path = Path({str(snapshot)!r})\n"
                "for action in (path.read_bytes, lambda: path.write_text('tampered')):\n"
                "    try: action(); print('accessible')\n"
                "    except PermissionError: print('denied')\n"
            )
            result = await self.execute(session, inspection)
            self.assertEqual(result["exit_code"], 0, result)
            self.assertEqual(result["stdout"], "denied\ndenied\n")
            self.assertEqual(result["submission"]["run_call"], 1)
            self.assertFalse(result["submitted"])
        freeze_submission(self.run_dir)
        self.assertEqual((self.run_dir / "solution.py").read_text(), source)

    async def test_inspection_only_is_ungraded_and_boolean_is_strict(self):
        async with self.connect(limit=1) as session:
            response = await session.call_tool("run_solution", {"code": "print(1)", "submit": "true"})
            self.assertTrue(response.isError)
            result = await self.execute(session, "print(42)")
            self.assertEqual(result["run_call"], 1)
        with self.assertRaisesRegex(RuntimeError, "No explicit submission"):
            freeze_submission(self.run_dir)


if __name__ == "__main__":
    unittest.main()
