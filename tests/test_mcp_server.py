import contextlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


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

    async def execute(self, session, source):
        response = await session.call_tool("run_solution", {"code": source})
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


if __name__ == "__main__":
    unittest.main()
