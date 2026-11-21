from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.chat import router as chat_router
from app.api.conversations import router as conversations_router
from app.api.health import router as health_router
from app.config import Settings, get_settings
from app.llm.registry import build_provider
from app.observability.logging import configure_logging
from app.orchestrator.summary_service import SummaryService
from app.storage.db import build_engine, build_session_factory

WEB_DIR = Path(__file__).resolve().parent.parent / "web"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    await app.state.engine.dispose()


def create_app(settings: Settings | None = None) -> FastAPI:
    configure_logging()
    settings = settings or get_settings()

    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.state.settings = settings
    app.state.provider = build_provider(settings)
    app.state.engine = build_engine(settings.database_url, settings.db_echo)
    app.state.session_factory = build_session_factory(app.state.engine)

    summary_settings = settings.model_copy(
        update={
            "llm_model": settings.summary_model or settings.llm_model,
            "llm_max_tokens": settings.summary_max_tokens,
            "llm_temperature": settings.summary_temperature,
        }
    )
    app.state.summary_provider = build_provider(summary_settings)
    app.state.summary_service = SummaryService(
        app.state.session_factory,
        app.state.summary_provider,
        settings,
    )

    app.include_router(health_router)
    app.include_router(chat_router)
    app.include_router(conversations_router)

    if WEB_DIR.exists():
        app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")

    return app
