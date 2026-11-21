import math

from app.llm.base import Message

MESSAGE_OVERHEAD = 4


def _is_cjk(char: str) -> bool:
    code = ord(char)
    return (
        0x3400 <= code <= 0x4DBF
        or 0x4E00 <= code <= 0x9FFF
        or 0xF900 <= code <= 0xFAFF
    )


def estimate_text(text: str) -> int:
    """Rough token estimate: CJK ~1 token/char, other ~4 chars/token.

    This is intentionally approximate. The abstraction lets P2/P3 swap in a real
    tokenizer later without changing the context builder.
    """

    if not text:
        return 0

    cjk = sum(1 for char in text if _is_cjk(char))
    other = len(text) - cjk
    return cjk + math.ceil(other / 4)


def estimate_message(message: Message) -> int:
    return estimate_text(message.content) + MESSAGE_OVERHEAD


def estimate_messages(messages: list[Message]) -> int:
    return sum(estimate_message(message) for message in messages)
