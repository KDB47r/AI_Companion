import logging
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.orchestrator.chat_service import stream_turn
from app.orchestrator.context_builder import build_p0_messages
from app.orchestrator.events import format_sse, heartbeat
from app.security.auth import verify_token

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])

SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


class ChatRequest(BaseModel):
    conversation_id: str | None = Field(default=None, max_length=128)
    message: str = Field(min_length=1, max_length=8000)
    client_message_id: str | None = Field(default=None, max_length=128)
    persona_id: str = Field(default="default", max_length=64)


@router.post("/v1/chat/stream")
async def chat_stream(
    payload: ChatRequest,
    request: Request,
    _: None = Depends(verify_token),
) -> StreamingResponse:
    settings = request.app.state.settings
    provider = request.app.state.provider

    conversation_id = payload.conversation_id or f"c_{uuid4().hex}"
    message_id = f"m_{uuid4().hex}"
    run_id = f"r_{uuid4().hex}"
    created_at = datetime.now(timezone.utc).isoformat()
    messages = build_p0_messages(payload.message)

    logger.info(
        "chat stream start conversation_id=%s message_id=%s run_id=%s provider=%s model=%s",
        conversation_id,
        message_id,
        run_id,
        settings.llm_provider,
        settings.llm_model,
    )

    async def event_source():
        event_id = 0
        try:
            async for event in stream_turn(
                provider,
                messages,
                conversation_id=conversation_id,
                message_id=message_id,
                run_id=run_id,
                created_at=created_at,
                heartbeat_seconds=settings.sse_heartbeat_seconds,
            ):
                if await request.is_disconnected():
                    logger.info("client disconnected run_id=%s", run_id)
                    break

                if event is None:
                    yield heartbeat()
                    continue

                event_id += 1
                yield format_sse(event.event, event.data, event_id)
        except Exception:
            logger.exception("unexpected chat stream error run_id=%s", run_id)
            event_id += 1
            yield format_sse(
                "error",
                {
                    "code": "INTERNAL_ERROR",
                    "message": "服务内部错误",
                    "retryable": False,
                    "run_id": run_id,
                },
                event_id,
            )
        finally:
            logger.info("chat stream end run_id=%s", run_id)

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )
