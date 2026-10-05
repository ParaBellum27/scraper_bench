"""Provider/model configuration for benchmark runs.

API keys are read from environment variables only. Never commit secrets.
"""

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class ModelConfig:
    provider: str
    model: str
    api_key_env: str

    def api_key(self) -> str:
        value = os.getenv(self.api_key_env)
        if not value:
            raise RuntimeError(f"Missing environment variable: {self.api_key_env}")
        return value


MODELS = {
    "luna": ModelConfig("openai", "gpt-6-luna", "OPENAI_API_KEY"),
    "mistral_medium_3_5": ModelConfig("mistral", "mistral-medium-3-5", "MISTRAL_API_KEY"),
    "gemini_3_8_flash": ModelConfig("gemini", "gemini-3.8-flash", "GEMINI_API_KEY"),
    # Optional calibration model. Set the exact Claude model ID at run time.
    "claude": ModelConfig("anthropic", os.getenv("CLAUDE_MODEL", ""), "ANTHROPIC_API_KEY"),
}

MAX_AGENT_TURNS = int(os.getenv("MAX_AGENT_TURNS", "20"))
MAX_RUN_CALLS = int(os.getenv("MAX_RUN_CALLS", "12"))
EXECUTION_TIMEOUT_SECONDS = int(os.getenv("EXECUTION_TIMEOUT_SECONDS", "10"))
