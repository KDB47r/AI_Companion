from app.llm.base import Message
from app.orchestrator.context_builder import build_messages, build_p0_messages


def test_build_p0_messages_has_system_then_user():
    messages = build_p0_messages("你好")

    assert [message.role for message in messages] == ["system", "user"]
    assert messages[-1].content == "你好"
    assert messages[0].content


def test_build_messages_injects_history_between_system_and_user():
    history = [
        Message(role="user", content="我叫小明"),
        Message(role="assistant", content="你好，小明"),
    ]

    messages = build_messages(history, "我叫什么")

    assert [message.role for message in messages] == [
        "system",
        "user",
        "assistant",
        "user",
    ]
    assert messages[1].content == "我叫小明"
    assert messages[2].content == "你好，小明"
    assert messages[-1].content == "我叫什么"


def test_build_messages_drops_empty_and_non_dialog_roles():
    history = [
        Message(role="system", content="应该被忽略"),
        Message(role="user", content=""),
        Message(role="assistant", content="保留"),
    ]

    messages = build_messages(history, "hi")

    assert [message.role for message in messages] == ["system", "assistant", "user"]
    assert messages[1].content == "保留"
