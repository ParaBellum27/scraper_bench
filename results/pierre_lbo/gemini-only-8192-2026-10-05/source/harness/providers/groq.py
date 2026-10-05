from harness.providers.common import OpenAICompatibleProvider


class GroqProvider(OpenAICompatibleProvider):
    token_cap_field = "max_completion_tokens"
