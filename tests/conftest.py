import os
from typing import AsyncGenerator

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

# Set test env vars before importing app
os.environ["AI_SERVICE_API_KEY"] = "test-api-key"
os.environ["SQLITE_DB_PATH"] = "./data/test-glowdesk-ai.db"
os.environ["OPENAI_API_KEY"] = "test-openai-key"

from src.db.database import init_db  # noqa: E402
from src.main import app  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client for testing async endpoints."""
    await init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def api_key_headers() -> dict[str, str]:
    return {"X-API-Key": "test-api-key", "X-Request-ID": "test-request-id"}


@pytest.fixture
def invalid_api_key_headers() -> dict[str, str]:
    return {"X-API-Key": "wrong-key", "X-Request-ID": "test-request-id"}
