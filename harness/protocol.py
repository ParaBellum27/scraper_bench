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
