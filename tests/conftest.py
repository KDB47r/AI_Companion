import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.main import create_app


@pytest.fixture
def settings() -> Settings:
    return Settings(
        dev_token="test-token",
        llm_provider="fake",
        fake_response="你好呀，我是小火。",
        fake_delay_seconds=0.0,
        sse_heartbeat_seconds=0.0,
    )


@pytest.fixture
def app(settings: Settings):
    return create_app(settings)


@pytest_asyncio.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client
