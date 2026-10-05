from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class ToolCall:
    name: str
    arguments: Dict[str, Any]
    call_id: Optional[str] = None


@dataclass
class ModelResponse:
    text: str
    tool_calls: List[ToolCall]
    raw: Any = None


class ResponseError(RuntimeError):
    """Categorized provider/agent failure with optional transport-sanitized evidence."""

    def __init__(self, message: str, *, category: str, raw: Any = None):
        super().__init__(message)
        self.category = category
        self.raw = raw
