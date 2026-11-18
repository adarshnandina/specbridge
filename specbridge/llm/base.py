"""Provider protocol and shared result types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

Message = dict[str, Any]


@dataclass
class ToolCall:
    name: str
    input: dict[str, Any]
    id: str = "toolu_0"


@dataclass
class LLMRequest:
    messages: list[Message]
    system: str = ""
    tools: list[dict[str, Any]] | None = None
    tool_choice: dict[str, Any] | None = None
    max_tokens: int = 1024
    temperature: float = 0.0
    purpose: str = "qa"
    prompt_version: str | None = None
    model: str = ""


@dataclass
class LLMResult:
    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""
    latency_ms: int = 0
    cache_hit: bool = False
    provider: str = ""


class LLMProvider(Protocol):
    name: str

    def complete(self, req: LLMRequest) -> LLMResult: ...


def pydantic_tool(name: str, description: str, model_cls: Any) -> dict[str, Any]:
    """Build an Anthropic tool definition whose input schema comes from a Pydantic model."""
    return {
        "name": name,
        "description": description,
        "input_schema": model_cls.model_json_schema(),
    }


def forced(name: str) -> dict[str, Any]:
    return {"type": "tool", "name": name}
