from functools import lru_cache
from pathlib import Path

from app.llm.base import Message

PROMPT_DIR = Path(__file__).resolve().parent.parent / "prompts"
SYSTEM_PROMPT_PATH = PROMPT_DIR / "system.md"

DEFAULT_SYSTEM_PROMPT = "你是一个温和、简短回应的 AI 伙伴。不要假装是人类。"
PROMPT_VERSION = "p1-system-v1"


@lru_cache
def load_system_prompt() -> str:
    try:
        return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return DEFAULT_SYSTEM_PROMPT


def build_messages(history: list[Message], user_message: str) -> list[Message]:
    """P1 context: system + recent completed history + current user message."""

    safe_history = [
        message
        for message in history
        if message.role in ("user", "assistant") and message.content
    ]
    return [
        Message(role="system", content=load_system_prompt()),
        *safe_history,
        Message(role="user", content=user_message),
    ]


def build_p0_messages(user_message: str) -> list[Message]:
    """Backward-compatible single-turn builder used by P0 tests."""

    return build_messages([], user_message)
