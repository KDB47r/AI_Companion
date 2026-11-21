from app.orchestrator.context_builder import build_p0_messages


def test_build_p0_messages_has_system_then_user():
    messages = build_p0_messages("你好")

    assert [message.role for message in messages] == ["system", "user"]
    assert messages[-1].content == "你好"
    assert messages[0].content
