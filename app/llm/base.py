from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Literal, Protocol

Role = Literal["system", "user", "assistant", "tool"]


@dataclass(slots=True)
class Message:
    role: Role
    content: str


@dataclass(slots=True)
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, object]


@dataclass(slots=True)
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0


@dataclass(slots=True)
class StreamEvent:
    type: Literal["text_delta", "reasoning_delta", "tool_call", "usage", "end"]
    delta: str = ""
    tool_call: dict[str, object] | None = None
    usage: Usage | None = None
    finish_reason: str | None = None


class LLMProvider(Protocol):
    def stream(
        self,
        messages: list[Message],
        tools: list[ToolSpec] | None = None,
    ) -> AsyncIterator[StreamEvent]:
        ...
