"""OpenAI-compatible message handling; the supplied transport owns all HTTP."""

import json
from typing import Any

from harness.protocol import ModelResponse, ResponseError, ToolCall


RUN_SOLUTION_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "run_solution",
        "description": (
            "Execute Python with public JSON stdin. Inspection/debugging defaults "
            "to submit=False and does not change the submission. Set submit=True "
            "to protect these exact source bytes as your final standalone program. "
            "Only the last explicit submission is graded; none means ungraded. "
            "Every accepted call consumes execution budget, including submissions."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "code": {"type": "string"},
                "submit": {"type": "boolean", "default": False},
            },
            "required": ["code"],
            "additionalProperties": False,
        },
    },
}


def completion_finish_reason(raw):
    """Validate the completion envelope before looking at any tool arguments."""
    if not isinstance(raw, dict):
        raise ResponseError("Completion must be a JSON object", category="protocol", raw=raw)
    choices = raw.get("choices")
    if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
        raise ResponseError("Completion must contain exactly one choice", category="protocol", raw=raw)
    reason = choices[0].get("finish_reason")
    if not isinstance(reason, str) or not reason:
        raise ResponseError("Completion has no valid finish_reason", category="protocol", raw=raw)
    if reason.lower() in {"length", "max_tokens", "max_completion_tokens"}:
        raise ResponseError("Provider output was truncated; no tool arguments executed", category="truncation", raw=raw)
    return reason


class OpenAICompatibleProvider:
    token_cap_field = "max_tokens"

    def __init__(self, model: str, max_tokens: int, transport):
        if not model or type(max_tokens) is not int or max_tokens <= 0:
            raise ValueError("A model and positive integer output cap are required")
        if not callable(getattr(transport, "post", None)):
            raise TypeError("A shared guarded transport is required")
        self.model = model
        self.max_tokens = max_tokens
        self.transport = transport

    def generate(self, messages):
        payload = {
            "model": self.model,
            "messages": messages,
            self.token_cap_field: self.max_tokens,
            "parallel_tool_calls": False,
            "tools": [RUN_SOLUTION_TOOL],
        }
        raw = self.transport.post(payload, max_output_tokens=self.max_tokens)
        reason = completion_finish_reason(raw)
        message = raw["choices"][0].get("message")
        if not isinstance(message, dict) or message.get("role") != "assistant":
            raise ResponseError("Completion has no assistant message", category="protocol", raw=raw)
        content = message.get("content")
        if content is None:
            text = ""
        elif isinstance(content, str):
            text = content
        elif isinstance(content, list) and all(isinstance(chunk, dict) for chunk in content):
            texts = [chunk.get("text") for chunk in content if chunk.get("type") == "text"]
            if not all(isinstance(value, str) for value in texts):
                raise ResponseError("Assistant text content is malformed", category="protocol", raw=raw)
            text = "\n".join(texts)
        else:
            raise ResponseError("Assistant content is malformed", category="protocol", raw=raw)
        raw_calls = message.get("tool_calls")
        if raw_calls is None:
            raw_calls = []
        if not isinstance(raw_calls, list):
            raise ResponseError("Assistant tool_calls must be an array", category="protocol", raw=raw)
        if reason == "tool_calls" and not raw_calls:
            raise ResponseError("Tool-call completion contains no calls", category="protocol", raw=raw)
        calls = []
        call_ids = set()
        # Parse the entire turn before returning: a malformed later call must not
        # cause an earlier call to execute from a partially accepted response.
        for call in raw_calls:
            if not isinstance(call, dict) or call.get("type") != "function":
                raise ResponseError("Malformed function tool call", category="protocol", raw=raw)
            function = call.get("function")
            call_id = call.get("id")
            if (not isinstance(function, dict) or not isinstance(call_id, str)
                    or not call_id or call_id in call_ids
                    or not isinstance(function.get("name"), str) or not function["name"]
                    or not isinstance(function.get("arguments"), str)):
                raise ResponseError("Malformed function tool call fields", category="protocol", raw=raw)
            try:
                arguments = json.loads(function["arguments"])
            except (ValueError, RecursionError):
                raise ResponseError("Tool arguments are not complete JSON", category="protocol", raw=raw) from None
            if not isinstance(arguments, dict):
                raise ResponseError("Tool arguments must be a JSON object", category="protocol", raw=raw)
            calls.append(ToolCall(name=function["name"], arguments=arguments, call_id=call_id))
            call_ids.add(call_id)
        return ModelResponse(text=text, tool_calls=calls, raw=raw)

    def assistant_message(self, response):
        # Replay the entire provider message, including reasoning fields and
        # nested Gemini extra_content.google.thought_signature. No allowlist:
        # stripping otherwise unknown fields can invalidate the next turn.
        return response.raw["choices"][0]["message"]
