import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from harness.agent import Agent
from harness.protocol import ModelResponse, ResponseError, ToolCall
from harness.providers.gemini import GeminiProvider
from harness.providers.groq import GroqProvider
from harness.providers.mistral import MistralProvider


def completion(arguments=None, *, reason=None, message_extra=None):
    message = {"role": "assistant", "content": "done" if arguments is None else None}
    if arguments is not None:
        message["tool_calls"] = [{
            "id": "call-1", "type": "function",
            "function": {"name": "run_solution", "arguments": arguments},
        }]
    message.update(message_extra or {})
    return {
        "model": "resolved-model", "usage": {"prompt_tokens": 20, "completion_tokens": 10, "total_tokens": 30},
        "choices": [{"finish_reason": reason or ("tool_calls" if arguments is not None else "stop"), "message": message}],
    }


def native_completion(*, parts=None, reason="STOP"):
    return {
        "modelVersion": "gemini-3.8-flash",
        "candidates": [{"finishReason": reason, "content": {
            "role": "model", "parts": parts if parts is not None else [{"text": "done"}],
        }}],
        "usageMetadata": {"promptTokenCount": 20, "candidatesTokenCount": 10,
                          "thoughtsTokenCount": 7, "totalTokenCount": 37},
    }


class RecordingTransport:
    def __init__(self, *responses):
        self.responses = iter(responses)
        self.requests = []

    def post(self, payload, *, max_output_tokens):
        self.requests.append((copy.deepcopy(payload), max_output_tokens))
        response = next(self.responses)
        if isinstance(response, Exception):
            raise response
        return response


class AdapterTests(unittest.TestCase):
    def test_compatibility_replays_full_message_and_requested_output_cap(self):
        for provider_class, field, model in (
            (GroqProvider, "max_completion_tokens", "openai/gpt-oss-120b"),
            (MistralProvider, "max_tokens", "mistral-medium-latest"),
        ):
            with self.subTest(provider=provider_class.__name__):
                first = completion('{"code":"print(1)","submit":true}', message_extra={
                    "reasoning": "provider reasoning", "extra_content": {"google": {"thought_signature": "opaque"}},
                })
                first["choices"][0]["message"]["tool_calls"][0]["extra_content"] = {
                    "google": {"thought_signature": "nested-opaque"},
                }
                transport = RecordingTransport(first, completion())
                provider = provider_class(model, 4096, transport)
                messages = [{"role": "user", "content": "task"}]
                response = provider.generate(messages)
                self.assertTrue(response.tool_calls[0].arguments["submit"])
                self.assertIs(response.raw, first)
                messages.extend([provider.assistant_message(response), {
                    "role": "tool", "tool_call_id": "call-1", "name": "run_solution", "content": "{}",
                }])
                provider.generate(messages)
                sent, cap = transport.requests[1]
                self.assertEqual(sent["messages"][1], first["choices"][0]["message"])
                self.assertEqual(sent[field], cap)
                self.assertEqual(cap, 4096)
                self.assertEqual(sent["model"], model)
                self.assertFalse(sent["parallel_tool_calls"])
                self.assertEqual([tool["function"]["name"] for tool in sent["tools"]], ["run_solution"])
                self.assertNotIn("temperature", sent)
                self.assertNotIn("reasoning_effort", sent)

    def test_transport_is_mandatory_and_errors_keep_categories(self):
        with self.assertRaises(TypeError):
            MistralProvider("mistral-medium-latest", 4096, None)
        error = ResponseError("denied", category="access")
        provider = GroqProvider("openai/gpt-oss-120b", 4096, RecordingTransport(error))
        with self.assertRaises(ResponseError) as caught:
            provider.generate([])
        self.assertIs(caught.exception, error)

    def test_truncation_is_detected_before_argument_parsing(self):
        for reason in ("length", "max_tokens", "MAX_TOKENS"):
            raw = completion('{"code":"unfinished', reason=reason)
            provider = MistralProvider("mistral-medium-latest", 4096, RecordingTransport(raw))
            with self.subTest(reason=reason), self.assertRaises(ResponseError) as caught:
                provider.generate([])
            self.assertEqual(caught.exception.category, "truncation")
            self.assertIs(caught.exception.raw, raw)

    def test_malformed_response_and_later_tool_are_protocol_errors(self):
        later_bad = completion('{"code":"first"}')
        later_bad["choices"][0]["message"]["tool_calls"].append({
            "id": "call-2", "type": "function", "function": {"name": "run_solution", "arguments": "{"},
        })
        missing_message = {"choices": [{"finish_reason": "stop"}]}
        for raw in (None, [], {}, {"choices": []}, missing_message,
                    completion("{"), completion("[]"), later_bad):
            provider = GroqProvider("openai/gpt-oss-120b", 4096, RecordingTransport(raw))
            with self.subTest(raw=raw), self.assertRaises(ResponseError) as caught:
                provider.generate([])
            self.assertEqual(caught.exception.category, "protocol")
            self.assertIs(caught.exception.raw, raw)

    def test_native_gemini_replays_signatures_ids_and_tool_results(self):
        parts = [
            {"text": "private thought", "thought": True, "thoughtSignature": "text-signature"},
            {"functionCall": {"id": "native-1", "name": "run_solution", "args": {"code": "one", "submit": True}},
             "thoughtSignature": "call-signature"},
            {"functionCall": {"name": "run_solution", "args": {"code": "two"}}, "thoughtSignature": "second-signature"},
        ]
        first = native_completion(parts=parts)
        transport = RecordingTransport(first, native_completion())
        provider = GeminiProvider("gemini-3.8-flash", 4096, transport)
        messages = [{"role": "system", "content": "rules"}, {"role": "user", "content": "task"}]
        response = provider.generate(messages)
        self.assertEqual(response.text, "")
        self.assertIs(response.raw["provider_response"], first)
        self.assertEqual(response.raw["usage"]["completion_tokens"], 17)
        messages.append(provider.assistant_message(response))
        for call in response.tool_calls:
            messages.append({"role": "tool", "name": call.name, "tool_call_id": call.call_id,
                             "content": json.dumps({"stdout": call.arguments["code"], "exit_code": 0})})
        provider.generate(messages)
        payload, cap = transport.requests[1]
        self.assertEqual(payload["contents"][1], first["candidates"][0]["content"])
        responses = payload["contents"][2]["parts"]
        self.assertEqual(responses[0]["functionResponse"]["id"], "native-1")
        self.assertNotIn("id", responses[1]["functionResponse"])
        self.assertEqual(responses[1]["functionResponse"]["response"]["stdout"], "two")
        self.assertEqual(payload["generationConfig"], {"maxOutputTokens": cap})
        self.assertEqual(payload["systemInstruction"], {"parts": [{"text": "rules"}]})
        declarations = payload["tools"][0]["functionDeclarations"]
        self.assertEqual(len(declarations), 1)
        self.assertFalse(declarations[0]["parametersJsonSchema"]["properties"]["submit"]["default"])

    def test_native_usage_infers_only_independently_proved_omitted_zeros(self):
        for metadata, expected_output, expected_thoughts in (
            ({"promptTokenCount": 20, "candidatesTokenCount": 10, "totalTokenCount": 30}, 10, 0),
            ({"promptTokenCount": 20, "thoughtsTokenCount": 7, "totalTokenCount": 27}, 7, 7),
            ({"promptTokenCount": 20, "totalTokenCount": 20}, None, None),
            ({"promptTokenCount": 20, "candidatesTokenCount": 10, "totalTokenCount": 37}, None, None),
            ({"promptTokenCount": 20, "thoughtsTokenCount": 7, "totalTokenCount": 37}, None, None),
            ({"promptTokenCount": 20, "candidatesTokenCount": 10,
              "thoughtsTokenCount": None, "totalTokenCount": 30}, None, None),
            ({"promptTokenCount": 20, "candidatesTokenCount": 10,
              "thoughtsTokenCount": False, "totalTokenCount": 30}, None, None),
            ({"promptTokenCount": 20, "candidatesTokenCount": 10,
              "thoughtsTokenCount": 7, "totalTokenCount": 30}, None, None),
        ):
            with self.subTest(metadata=metadata):
                raw = native_completion()
                raw["usageMetadata"] = metadata
                provider = GeminiProvider("gemini-3.8-flash", 4096, RecordingTransport(raw))
                usage = provider.generate([]).raw["usage"]
                if expected_output is None:
                    self.assertIsNone(usage)
                else:
                    self.assertEqual(usage["completion_tokens"], expected_output)
                    self.assertEqual(usage["completion_tokens_details"]["reasoning_tokens"], expected_thoughts)
                self.assertEqual(raw["usageMetadata"], metadata)

    def test_native_truncation_and_malformed_response_keep_raw_evidence(self):
        for raw, category in (
            (native_completion(parts=[{"functionCall": "partial"}], reason="MAX_TOKENS"), "truncation"),
            (native_completion(parts=[{"functionCall": {"name": "run_solution", "args": "partial"}}]), "protocol"),
            ({"candidates": []}, "protocol"),
            (native_completion(reason="SAFETY"), "provider"),
        ):
            provider = GeminiProvider("gemini-3.8-flash", 4096, RecordingTransport(raw))
            with self.subTest(category=category), self.assertRaises(ResponseError) as caught:
                provider.generate([])
            self.assertEqual(caught.exception.category, category)
            self.assertIs(caught.exception.raw, raw)


class AgentBoundaryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        self.workspace, self.run_dir = root / "public", root / "private"
        self.workspace.mkdir()
        self.run_dir.mkdir()
        session_patch = patch("harness.agent.SubmissionSession")
        self.session = session_patch.start().return_value
        self.addCleanup(session_patch.stop)
        self.session.execute.return_value = {"exit_code": 0, "run_call": 1, "stdout": "", "stderr": ""}
        self.now = 10.0
        clock_patch = patch("harness.agent.time.monotonic", side_effect=lambda: self.now)
        clock_patch.start()
        self.addCleanup(clock_patch.stop)

    def run_agent(self, provider, **kwargs):
        return Agent(provider, self.workspace, self.run_dir, "{}", max_steps=3, **kwargs).run("task")

    def trajectory(self):
        return json.loads((self.run_dir / "trajectory.json").read_text())

    def test_truncated_arguments_never_execute_and_evidence_is_saved(self):
        raw = completion('{"code":"partial', reason="length")
        provider = MistralProvider("mistral-medium-latest", 4096, RecordingTransport(raw))
        with self.assertRaises(ResponseError):
            self.run_agent(provider)
        self.session.execute.assert_not_called()
        evidence = self.trajectory()
        self.assertEqual(evidence["stop_reason"], "provider_truncation")
        self.assertEqual(evidence["error_category"], "truncation")
        self.assertEqual(evidence["error_response"], raw)

    def test_agent_rejects_truncation_even_from_already_parsed_provider(self):
        provider = Mock()
        provider.generate.return_value = ModelResponse("", [ToolCall("run_solution", {"code": "partial"}, "1")],
                                                        {"choices": [{"finish_reason": "max_tokens"}]})
        with self.assertRaises(ResponseError):
            self.run_agent(provider)
        self.session.execute.assert_not_called()
        provider.assistant_message.assert_not_called()

    def test_expired_deadline_stops_before_provider_request(self):
        provider = Mock()
        with self.assertRaises(ResponseError) as caught:
            self.run_agent(provider, deadline=10.0)
        self.assertEqual(caught.exception.category, "deadline")
        provider.generate.assert_not_called()
        self.session.execute.assert_not_called()

    def test_provider_crossing_deadline_does_not_start_tool(self):
        provider = Mock()
        def generate(messages):
            self.now = 21.0
            return ModelResponse("", [ToolCall("run_solution", {"code": "late"}, "1")], completion())
        provider.generate.side_effect = generate
        with self.assertRaises(ResponseError):
            self.run_agent(provider, deadline=20.0)
        self.session.execute.assert_not_called()
        self.assertEqual(provider.generate.call_count, 1)
        self.assertEqual(self.trajectory()["error_category"], "deadline")

    def test_tool_timeout_uses_remaining_time_and_stops_next_call(self):
        raw = completion('{"code":"first"}')
        raw["choices"][0]["message"]["tool_calls"].append({
            "id": "call-2", "type": "function", "function": {"name": "run_solution", "arguments": '{"code":"second"}'},
        })
        transport = RecordingTransport(raw)
        provider = MistralProvider("mistral-medium-latest", 4096, transport)
        def execute(*args):
            self.assertEqual(self.session.timeout, 2.5)
            self.now = 12.5
            return {"exit_code": 124, "run_call": 1, "stdout": "", "stderr": "timeout"}
        self.session.execute.side_effect = execute
        with self.assertRaises(ResponseError):
            self.run_agent(provider, deadline=12.5, timeout=30)
        self.assertEqual(self.session.execute.call_count, 1)
        self.assertEqual(len(transport.requests), 1)
        self.assertEqual(self.trajectory()["steps"][0]["tool_results"][0]["result"]["exit_code"], 124)

    def test_candidate_execution_failure_is_tool_feedback_not_provider_failure(self):
        self.session.execute.return_value = {"exit_code": 1, "run_call": 1, "stderr": "candidate exception"}
        transport = RecordingTransport(completion('{"code":"raise Exception()"}'), completion())
        trajectory = self.run_agent(MistralProvider("mistral-medium-latest", 4096, transport), timeout=30)
        self.assertEqual(trajectory["stop_reason"], "stop")
        self.assertNotIn("error_category", trajectory)
        self.assertEqual(trajectory["steps"][0]["tool_results"][0]["result"]["exit_code"], 1)
        self.assertEqual(self.session.timeout, 30)
        tool_message = transport.requests[1][0]["messages"][-1]
        self.assertEqual(json.loads(tool_message["content"])["stderr"], "candidate exception")

    def test_protocol_and_transport_categories_are_not_candidate_errors(self):
        for response, category in (({}, "protocol"), (ResponseError("quota", category="quota"), "quota")):
            provider = GroqProvider("openai/gpt-oss-120b", 4096, RecordingTransport(response))
            with self.subTest(category=category), self.assertRaises(ResponseError):
                self.run_agent(provider)
            self.assertEqual(self.trajectory()["error_category"], category)
            self.session.execute.assert_not_called()


if __name__ == "__main__":
    unittest.main()
