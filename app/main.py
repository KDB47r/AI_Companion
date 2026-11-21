from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.chat import router as chat_router
from app.api.health import router as health_router
from app.config import Settings, get_settings
from app.llm.registry import build_provider
from app.observability.logging import configure_logging

WEB_DIR = Path(__file__).resolve().parent.parent / "web"


def create_app(settings: Settings | None = None) -> FastAPI:
    configure_logging()
    settings = settings or get_settings()

    app = FastAPI(title=settings.app_name)
    app.state.settings = settings
    app.state.provider = build_provider(settings)

    app.include_router(health_router)
    app.include_router(chat_router)

    if WEB_DIR.exists():
        app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")

    return app


app = create_app()
