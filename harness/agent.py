import json
from pathlib import Path

from harness.config import EXECUTION_TIMEOUT_SECONDS, MAX_AGENT_TURNS, MAX_RUN_CALLS
from harness.executor import run_solution


SYSTEM_PROMPT = """You are participating in a finance coding benchmark.
Solve the supplied task by writing executable Python, not hard-coded public outputs.

Your workspace contains only task.md, fcff2st.xlsx, and inputs/base_case.json.
Use run_solution(code) to replace solution.py and execute that source with the public
base-case JSON on stdin. Python's standard library and openpyxl are available.
You may first write inspection scripts to examine the workbook's formulas and cached
values. Each tool call overwrites solution.py; your LAST saved file is your submission.
The final program must read one JSON object on stdin and write one JSON object on stdout.
It must not depend on the workbook or any supporting files at final evaluation.

There is no network access. Do not access files outside the public workspace.
Only public execution feedback is available; hidden grading happens after you finish.
Test your final program using run_solution before finishing with a short final message.
"""


class Agent:
    def __init__(
        self, provider, workspace: Path, run_dir: Path, base_input: str,
        max_steps: int = MAX_AGENT_TURNS, max_run_calls: int = MAX_RUN_CALLS,
        timeout: float = EXECUTION_TIMEOUT_SECONDS,
    ):
        self.provider = provider
        self.workspace = workspace
        self.run_dir = run_dir
        self.base_input = base_input
        self.max_steps = max_steps
        self.max_run_calls = max_run_calls
        self.timeout = timeout

    def run(self, task_prompt: str):
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT + (
                f"\nLimits: {self.max_steps} model turns, {self.max_run_calls} executions, "
                f"{self.timeout} seconds per execution."
            )},
            {"role": "user", "content": task_prompt},
        ]
        trajectory = {
            "messages": messages, "steps": [], "run_calls": 0, "stop_reason": "max_steps",
        }
        trajectory_path = self.run_dir / "trajectory.json"

        def save():
            trajectory_path.write_text(json.dumps(trajectory, indent=2))

        save()
        try:
            for step in range(self.max_steps):
                response = self.provider.generate(messages)
                messages.append(self.provider.assistant_message(response))
                entry = {"step": step + 1, "response": response.raw, "tool_results": []}
                trajectory["steps"].append(entry)
                save()
                print(f"Turn {step + 1}: {len(response.tool_calls)} tool call(s)", flush=True)
                if not response.tool_calls:
                    trajectory["stop_reason"] = response.raw["choices"][0]["finish_reason"]
                    break
                for call in response.tool_calls:
                    if call.name != "run_solution":
                        result = {"error": f"Unknown tool: {call.name}"}
                    elif trajectory["run_calls"] >= self.max_run_calls:
                        result = {"error": "Execution limit reached; the last saved file is final."}
                    elif not isinstance(call.arguments, dict) or not isinstance(call.arguments.get("code"), str):
                        result = {"error": "run_solution requires a string code argument."}
                    else:
                        trajectory["run_calls"] += 1
                        source = call.arguments["code"]
                        # Never follow a symlink left by a previous candidate execution.
                        solution = self.workspace / "solution.py"
                        solution.unlink(missing_ok=True)
                        solution.write_text(source)
                        (self.run_dir / f"step-{step + 1}-call-{trajectory['run_calls']}.py").write_text(source)
                        result = run_solution(str(solution), timeout=self.timeout, stdin=self.base_input)
                    entry["tool_results"].append({"call_id": call.call_id, "result": result})
                    messages.append({
                        "role": "tool", "name": call.name, "tool_call_id": call.call_id,
                        "content": json.dumps(result),
                    })
                    print(f"  {call.name}: exit={result.get('exit_code', 'error')}", flush=True)
                    save()
                if trajectory["run_calls"] >= self.max_run_calls:
                    trajectory["stop_reason"] = "max_run_calls"
                    break
        except Exception as exc:
            trajectory["stop_reason"] = "harness_error"
            trajectory["error"] = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            save()
        return trajectory
