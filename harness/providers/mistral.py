import json
import os
import urllib.error
import urllib.request

from harness.protocol import ModelResponse, ToolCall


class MistralProvider:
    def __init__(self, model: str, max_tokens: int = 8192):
        self.model = model
        self.max_tokens = max_tokens
        self.api_key = os.environ["MISTRAL_API_KEY"]

    def generate(self, messages):
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0,
            "max_tokens": self.max_tokens,
            "parallel_tool_calls": False,
            "tools": [{
                "type": "function",
                "function": {
                    "name": "run_solution",
                    "description": (
                        "Replace solution.py with the supplied Python source and execute it "
                        "with the public base-case JSON on stdin. Returns exit_code, stdout, "
                        "stderr. Use Python to inspect public workbook/input files. "
                        "Your last saved solution.py is the final submission."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {"code": {"type": "string"}},
                        "required": ["code"],
                        "additionalProperties": False,
                    },
                },
            }],
        }
        request = urllib.request.Request(
            "https://api.mistral.ai/v1/chat/completions",
            data=json.dumps(payload).encode(),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                raw = json.load(response)
        except urllib.error.HTTPError as exc:
            detail = exc.read(4096).decode("utf-8", errors="replace").replace(self.api_key, "[redacted]")
            retry_after = exc.headers.get("Retry-After")
            hint = f"; Retry-After={retry_after}" if retry_after else ""
            raise RuntimeError(f"Mistral completion failed: HTTP {exc.code}{hint}: {detail}") from None

        message = raw["choices"][0]["message"]
        content = message.get("content") or ""
        text = content if isinstance(content, str) else "\n".join(
            chunk.get("text", "") for chunk in content if chunk.get("type") == "text"
        )
        calls = [
            ToolCall(
                name=call["function"]["name"],
                arguments=json.loads(call["function"]["arguments"]),
                call_id=call["id"],
            )
            for call in message.get("tool_calls") or []
        ]
        return ModelResponse(text=text, tool_calls=calls, raw=raw)

    def assistant_message(self, response):
        message = response.raw["choices"][0]["message"]
        return {key: message[key] for key in ("role", "content", "tool_calls") if key in message}