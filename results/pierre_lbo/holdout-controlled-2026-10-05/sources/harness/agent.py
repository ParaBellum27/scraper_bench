import json
import time
from pathlib import Path

from harness.config import EXECUTION_TIMEOUT_SECONDS, MAX_AGENT_TURNS, MAX_RUN_CALLS
from harness.protocol import ResponseError
from harness.providers.common import completion_finish_reason
from harness.submission import SubmissionSession


SYSTEM_PROMPT = """You are participating in a finance coding benchmark.
Solve the supplied task by writing executable Python, not hard-coded public outputs.

Your workspace contains only task.md, {workbook_name}, and inputs/base_case.json.
Use run_solution(code, submit=False) to execute inspection/debugging code with the
public base-case JSON on stdin. Python's standard library and openpyxl are available.
To submit your standalone final program, call run_solution(code, submit=True).
Only the last explicit submission is graded; inspection calls and workspace writes
never replace it. Without an explicit submission your attempt is ungraded.
Every accepted execution, including submissions, consumes one call; reserve a call
to submit. The exact supplied source is saved before execution, even if it errors.
The final program must read one JSON object on stdin and write one JSON object on stdout.
It must not depend on the workbook or any supporting files at final evaluation.

There is no network access. Do not access files outside the public workspace.
Only public execution feedback is available; hidden grading happens after you finish.
Submit your final program using run_solution(code, submit=True) before finishing.
"""


class Agent:
    def __init__(
        self, provider, workspace: Path, run_dir: Path, base_input: str,
        max_steps: int = MAX_AGENT_TURNS, max_run_calls: int = MAX_RUN_CALLS,
        timeout: float = EXECUTION_TIMEOUT_SECONDS, workbook_name: str = "fcff2st.xlsx",
        *, deadline: float | None = None, workflow_instruction: str = "",
    ):
        self.provider = provider
        self.workspace = workspace
        self.run_dir = run_dir
        self.base_input = base_input
        self.max_steps = max_steps
        self.max_run_calls = max_run_calls
        self.timeout = timeout
        self.workbook_name = workbook_name
        self.deadline = deadline
        self.workflow_instruction = workflow_instruction

    def run(self, task_prompt: str):
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT.format(workbook_name=self.workbook_name) + (
                f"\nLimits: {self.max_steps} model turns, {self.max_run_calls} executions, "
                f"{self.timeout} seconds per execution.\n{self.workflow_instruction}"
            )},
            {"role": "user", "content": task_prompt},
        ]
        trajectory = {
            "messages": messages, "steps": [], "run_calls": 0, "stop_reason": "max_steps",
        }
        trajectory_path = self.run_dir / "trajectory.json"
        session = SubmissionSession(self.workspace, self.run_dir, self.base_input, self.max_run_calls, self.timeout)

        def save():
            trajectory_path.write_text(json.dumps(trajectory, indent=2))


        def remaining_time():
            if self.deadline is None:
                return self.timeout
            remaining = self.deadline - time.monotonic()
            if remaining <= 0:
                raise ResponseError("Whole-run deadline reached", category="deadline")
            return min(self.timeout, remaining)
        save()
        try:
            for step in range(self.max_steps):
                remaining_time()
                response = self.provider.generate(messages)
                remaining_time()
                finish_reason = completion_finish_reason(response.raw)
                messages.append(self.provider.assistant_message(response))
                entry = {"step": step + 1, "response": response.raw, "tool_results": []}
                trajectory["steps"].append(entry)
                save()
                print(f"Turn {step + 1}: {len(response.tool_calls)} tool call(s)", flush=True)
                if not response.tool_calls:
                    trajectory["stop_reason"] = finish_reason
                    break
                for call in response.tool_calls:
                    session.timeout = remaining_time()
                    if call.name != "run_solution":
                        result = {"error": f"Unknown tool: {call.name}"}
                    elif not isinstance(call.arguments, dict) or set(call.arguments) - {"code", "submit"}:
                        result = {"error": "run_solution requires code and optional submit arguments."}
                    else:
                        result = session.execute(call.arguments.get("code"), call.arguments.get("submit", False))
                        if "run_call" in result:
                            trajectory["run_calls"] = result["run_call"]
                    entry["tool_results"].append({"call_id": call.call_id, "result": result})
                    messages.append({
                        "role": "tool", "name": call.name, "tool_call_id": call.call_id,
                        "content": json.dumps(result),
                    })
                    print(f"  {call.name}: exit={result.get('exit_code', 'error')}", flush=True)
                    save()
                    remaining_time()
                if trajectory["run_calls"] >= self.max_run_calls:
                    trajectory["stop_reason"] = "max_run_calls"
                    break
        except Exception as exc:
            category = getattr(exc, "category", "infrastructure")
            trajectory["stop_reason"] = {
                "truncation": "provider_truncation",
                "protocol": "provider_protocol_error",
            }.get(category, category + "_error")
            trajectory["error_category"] = category
            trajectory["error"] = f"{type(exc).__name__}: {exc}"
            raw = getattr(exc, "raw", None)
            if raw is not None:
                # Only JSON evidence is safe to persist; never mask the original
                # failure with serialization of an arbitrary exception object.
                try:
                    json.dumps(raw, allow_nan=False)
                except (TypeError, ValueError, RecursionError):
                    pass
                else:
                    trajectory["error_response"] = raw
            raise
        finally:
            save()
        return trajectory
