"""Native Gemini requests with lossless thought-signature conversation replay.

The compatibility guide does not currently document output-cap semantics. Use
native generationConfig.maxOutputTokens instead; reserve the hard model output
bound in the transport independently of this requested cap.
https://ai.google.dev/api/generate-content#GenerationConfig
"""

import json
from typing import Any, cast

from harness.protocol import ModelResponse, ResponseError, ToolCall
from harness.providers.common import OpenAICompatibleProvider, RUN_SOLUTION_TOOL


class GeminiProvider(OpenAICompatibleProvider):
    def generate(self, messages):
        contents: list[dict[str, Any]] = []
        system_parts = []
        native_ids = {}
        for message in messages:
            role = message["role"]
            if role == "system":
                system_parts.append({"text": message["content"]})
            elif role == "assistant":
                # Exact native content includes every thoughtSignature and part,
                # not just the functionCall extracted for local execution.
                contents.append(message["_gemini_content"])
                native_ids.update(message["_gemini_call_ids"])
            elif role == "tool":
                function_response = {
                    "name": message["name"],
                    "response": json.loads(message["content"]),
                }
                native_id = native_ids[message["tool_call_id"]]
                if native_id is not None:
                    function_response["id"] = native_id
                part: dict[str, Any] = {"functionResponse": function_response}
                if contents and contents[-1]["role"] == "user":
                    contents[-1]["parts"].append(part)
                else:
                    contents.append({"role": "user", "parts": [part]})
            else:
                contents.append({"role": "user", "parts": [{"text": message["content"]}]})
        function = RUN_SOLUTION_TOOL["function"]
        # Native schema uses its documented JSON-schema field to retain the
        # explicit submit=False default and additionalProperties=False contract.
        payload = {
            "contents": contents,
            "generationConfig": {"maxOutputTokens": self.max_tokens},
            "tools": [{"functionDeclarations": [{
                "name": function["name"],
                "description": function["description"],
                "parametersJsonSchema": function["parameters"],
            }]}],
        }
        if system_parts:
            payload["systemInstruction"] = {"parts": system_parts}
        # generateContent has no parallel_tool_calls flag; returned calls are
        # processed sequentially by Agent, never concurrently.
        raw = self.transport.post(payload, max_output_tokens=self.max_tokens)
        if not isinstance(raw, dict):
            raise ResponseError("Gemini completion must be an object", category="protocol", raw=raw)
        candidates = raw.get("candidates")
        if not isinstance(candidates, list) or len(candidates) != 1 or not isinstance(candidates[0], dict):
            feedback = raw.get("promptFeedback")
            category = "provider" if isinstance(feedback, dict) and feedback.get("blockReason") else "protocol"
            raise ResponseError("Gemini completion has no single candidate", category=category, raw=raw)
        candidate = candidates[0]
        reason = candidate.get("finishReason")
        if reason == "MAX_TOKENS":
            raise ResponseError("Provider output was truncated; no tool arguments executed", category="truncation", raw=raw)
        if not isinstance(reason, str) or not reason:
            raise ResponseError("Gemini completion has no finishReason", category="protocol", raw=raw)
        if reason != "STOP":
            raise ResponseError("Gemini generation stopped: " + reason, category="provider", raw=raw)
        content = candidate.get("content")
        if not isinstance(content, dict) or content.get("role") != "model":
            raise ResponseError("Gemini completion has no model content", category="protocol", raw=raw)
        parts = content.get("parts")
        if not isinstance(parts, list) or not parts:
            raise ResponseError("Gemini model parts are malformed", category="protocol", raw=raw)
        texts, calls, normalized_calls = [], [], []
        call_ids = {}
        for index, value in enumerate(parts):
            if not isinstance(value, dict):
                raise ResponseError("Gemini model part is malformed", category="protocol", raw=raw)
            part = cast(dict[str, Any], value)
            if "text" in part:
                if not isinstance(part["text"], str):
                    raise ResponseError("Gemini text part is malformed", category="protocol", raw=raw)
                if not part.get("thought"):
                    texts.append(part["text"])
            if "functionCall" not in part:
                continue
            function_call = part["functionCall"]
            if (not isinstance(function_call, dict)
                    or not isinstance(function_call.get("name"), str) or not function_call["name"]
                    or not isinstance(function_call.get("args"), dict)):
                raise ResponseError("Gemini functionCall is malformed", category="protocol", raw=raw)
            native_id = function_call.get("id")
            if native_id is not None and (not isinstance(native_id, str) or not native_id):
                raise ResponseError("Gemini functionCall id is malformed", category="protocol", raw=raw)
            # Native IDs are optional. Synthesized IDs are local correlation only
            # and are never sent as a fabricated native functionResponse.id.
            call_id = native_id if native_id is not None else f"gemini-{len(messages)}-{index}"
            if call_id in call_ids:
                raise ResponseError("Gemini functionCall ids repeat", category="protocol", raw=raw)
            call_ids[call_id] = native_id
            calls.append(ToolCall(function_call["name"], function_call["args"], call_id))
            normalized_calls.append({"id": call_id, "type": "function", "function": {
                "name": function_call["name"], "arguments": json.dumps(function_call["args"]),
            }})
        text = "\n".join(texts)
        assistant = {
            "role": "assistant", "content": text, "tool_calls": normalized_calls,
            "_gemini_content": content, "_gemini_call_ids": call_ids,
        }
        normalized = {
            "choices": [{"finish_reason": "tool_calls" if calls else "stop", "message": assistant}],
            "model": raw.get("modelVersion"),
            "usage": None,
            "provider_response": raw,
        }
        metadata = raw.get("usageMetadata")
        if isinstance(metadata, dict):
            prompt = metadata.get("promptTokenCount")
            candidates_count = metadata.get("candidatesTokenCount")
            thoughts = metadata.get("thoughtsTokenCount")
            total = metadata.get("totalTokenCount")
            # ProtoJSON may omit zero-valued scalars. Infer only an omitted
            # zero independently proved by the other three explicit counts.
            # https://protobuf.dev/programming-guides/json/#presence-and-default-values
            if "thoughtsTokenCount" not in metadata:
                if (type(prompt) is int and type(candidates_count) is int
                        and type(total) is int and total == prompt + candidates_count):
                    thoughts = 0
            if "candidatesTokenCount" not in metadata:
                if (type(prompt) is int and type(thoughts) is int
                        and "thoughtsTokenCount" in metadata
                        and type(total) is int and total == prompt + thoughts):
                    candidates_count = 0
            if (type(prompt) is int and prompt >= 0
                    and type(candidates_count) is int and candidates_count >= 0
                    and type(thoughts) is int and thoughts >= 0
                    and type(total) is int and total == prompt + candidates_count + thoughts):
                normalized["usage"] = {
                    "prompt_tokens": prompt,
                    "completion_tokens": candidates_count + thoughts,
                    "total_tokens": total,
                    "completion_tokens_details": {"reasoning_tokens": thoughts},
                }
        return ModelResponse(text=text, tool_calls=calls, raw=normalized)
