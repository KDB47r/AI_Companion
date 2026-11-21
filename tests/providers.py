import asyncio
from collections.abc import AsyncIterator

from app.llm.base import Message, StreamEvent, ToolSpec, Usage


class RecordingProvider:
    """Records the messages passed to the model, then streams a fixed reply."""

    def __init__(self, text: str = "收到。", delay: float = 0.0) -> None:
        self.text = text
        self.delay = delay
        self.calls: list[list[Message]] = []

    async def stream(
        self,
        messages: list[Message],
        tools: list[ToolSpec] | None = None,
    ) -> AsyncIterator[StreamEvent]:
        self.calls.append(list(messages))
        for char in self.text:
            if self.delay:
                await asyncio.sleep(self.delay)
            yield StreamEvent(type="text_delta", delta=char)

        yield StreamEvent(
            type="usage",
            usage=Usage(input_tokens=10, output_tokens=5),
        )
        yield StreamEvent(type="end", finish_reason="stop")


class FailingProvider:
    """Yields one partial delta, then fails, to test failure persistence."""

    def __init__(self, partial: str = "半句") -> None:
        self.partial = partial

    async def stream(
        self,
        messages: list[Message],
        tools: list[ToolSpec] | None = None,
    ) -> AsyncIterator[StreamEvent]:
        if self.partial:
            yield StreamEvent(type="text_delta", delta=self.partial)
        raise RuntimeError("provider boom")
