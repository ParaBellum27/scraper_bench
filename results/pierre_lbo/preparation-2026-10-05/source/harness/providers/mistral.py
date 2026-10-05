from harness.providers.common import OpenAICompatibleProvider


class MistralProvider(OpenAICompatibleProvider):
    token_cap_field = "max_tokens"