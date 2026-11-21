from functools import lru_cache
from pathlib import Path

from app.llm.base import Message

PROMPT_DIR = Path(__file__).resolve().parent.parent / "prompts"
SYSTEM_PROMPT_PATH = PROMPT_DIR / "system.md"

DEFAULT_SYSTEM_PROMPT = "你是一个温和、简短回应的 AI 伙伴。不要假装是人类。"


@lru_cache
def load_system_prompt() -> str:
    try:
        return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return DEFAULT_SYSTEM_PROMPT


def build_p0_messages(user_message: str) -> list[Message]:
    """P0 context: one system prompt + the current user message.

    P1 will replace this with history loading, token budgeting and summaries.
    """

    return [
        Message(role="system", content=load_system_prompt()),
        Message(role="user", content=user_message),
    ]
