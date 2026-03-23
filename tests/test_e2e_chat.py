"""End-to-end integration tests for Epic 5a — Story 5a.5.

All OpenAI calls are mocked. These tests verify the full flow:
chat request -> agent -> tools -> storage -> response.
"""

import os
from unittest.mock import AsyncMock, patch

import aiosqlite
import pytest
from httpx import AsyncClient

from src.agents.customer_chat_agent import reset_graph
from src.db.database import init_db

_TEST_DB = "./data/test-e2e.db"


@pytest.fixture(autouse=True)
async def _setup_e2e():
    """Set up clean test database and reset agent for each test."""
    os.environ["SQLITE_DB_PATH"] = _TEST_DB
    import src.config.settings as settings_mod
    settings_mod._settings = None

    reset_graph()
    await init_db()
    yield
    reset_graph()

    if os.path.exists(_TEST_DB):
        os.remove(_TEST_DB)
    settings_mod._settings = None


def _mock_agent_reply(reply_text: str):
    """Create a patch context that mocks the agent to return a simple reply."""
    return patch(
        "src.services.chat_service.invoke_agent",
        new_callable=AsyncMock,
        return_value=reply_text,
    )


def _mock_tenant_config(config: dict | None = None):
    """Create a patch context that mocks tenant config lookup."""
    return patch(
        "src.services.chat_service.get_tenant_config",
        new_callable=AsyncMock,
        return_value=config or {},
    )


@pytest.mark.asyncio
async def test_e2e_send_chat_get_response(
    async_client: AsyncClient,
    api_key_headers: dict[str, str],
) -> None:
    """Send a chat message and receive an AI response."""
    with _mock_agent_reply("Xin chao! Toi la tro ly."), _mock_tenant_config():
        response = await async_client.post(
            "/api/v1/chat",
            json={
                "conversationId": "e2e-conv-001",
                "message": "Xin chao",
                "tenantId": "e2e-tenant-001",
            },
            headers=api_key_headers,
        )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["reply"] == "Xin chao! Toi la tro ly."
    assert body["data"]["conversationId"] == "e2e-conv-001"


@pytest.mark.asyncio
async def test_e2e_multi_turn_conversation(
    async_client: AsyncClient,
    api_key_headers: dict[str, str],
) -> None:
    """Multi-turn: second message has access to first in history."""
    conv_id = "e2e-multi-turn"

    # First message
    with _mock_agent_reply("Chao ban! Toi giup gi?"), _mock_tenant_config():
        resp1 = await async_client.post(
            "/api/v1/chat",
            json={
                "conversationId": conv_id,
                "message": "Xin chao",
                "tenantId": "e2e-tenant-001",
            },
            headers=api_key_headers,
        )
    assert resp1.status_code == 200

    # Second message — agent should receive history
    with patch(
        "src.services.chat_service.invoke_agent",
        new_callable=AsyncMock,
        return_value="Cat toc gia 100k.",
    ) as mock_invoke, _mock_tenant_config():
        resp2 = await async_client.post(
            "/api/v1/chat",
            json={
                "conversationId": conv_id,
                "message": "Gia cat toc?",
                "tenantId": "e2e-tenant-001",
            },
            headers=api_key_headers,
        )

    assert resp2.status_code == 200
    # Verify agent received conversation history from first exchange
    call_kwargs = mock_invoke.call_args
    history = call_kwargs.kwargs.get(
        "conversation_history", call_kwargs[1].get("conversation_history", [])
    )
    assert len(history) == 2  # user + assistant from first turn


@pytest.mark.asyncio
async def test_e2e_conversation_stored_in_sqlite(
    async_client: AsyncClient,
    api_key_headers: dict[str, str],
) -> None:
    """Messages are persisted in SQLite after a chat exchange."""
    conv_id = "e2e-persist"

    with _mock_agent_reply("Da luu."), _mock_tenant_config():
        await async_client.post(
            "/api/v1/chat",
            json={
                "conversationId": conv_id,
                "message": "Luu tin nhan nay",
                "tenantId": "e2e-tenant-001",
            },
            headers=api_key_headers,
        )

    # Check SQLite directly
    db = await aiosqlite.connect(_TEST_DB)
    db.row_factory = aiosqlite.Row
    try:
        cursor = await db.execute(
            "SELECT id, tenant_id FROM conversations WHERE id = ?",
            (conv_id,),
        )
        conv = await cursor.fetchone()
        assert conv is not None
        assert conv["tenant_id"] == "e2e-tenant-001"

        cursor = await db.execute(
            "SELECT role, content FROM messages "
            "WHERE conversation_id = ? ORDER BY created_at",
            (conv_id,),
        )
        messages = await cursor.fetchall()
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Luu tin nhan nay"
        assert messages[1]["role"] == "assistant"
        assert messages[1]["content"] == "Da luu."
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_e2e_invalid_api_key(
    async_client: AsyncClient,
    invalid_api_key_headers: dict[str, str],
) -> None:
    """Invalid API key returns 401 with proper error format."""
    response = await async_client.post(
        "/api/v1/chat",
        json={
            "conversationId": "e2e-noauth",
            "message": "Hack attempt",
            "tenantId": "t-1",
        },
        headers=invalid_api_key_headers,
    )
    assert response.status_code == 401
    body = response.json()
    detail = body["detail"]
    assert detail["success"] is False
    assert detail["error"]["code"] == "AUTH_INVALID_API_KEY"


@pytest.mark.asyncio
async def test_e2e_openai_failure_graceful_error(
    async_client: AsyncClient,
    api_key_headers: dict[str, str],
) -> None:
    """When OpenAI fails, response returns structured error (no crash)."""
    with patch(
        "src.services.chat_service.invoke_agent",
        new_callable=AsyncMock,
        side_effect=Exception("OpenAI API error"),
    ), _mock_tenant_config():
        response = await async_client.post(
            "/api/v1/chat",
            json={
                "conversationId": "e2e-fail",
                "message": "Test failure",
                "tenantId": "e2e-tenant-001",
            },
            headers=api_key_headers,
        )

    # Should not crash — returns a structured error response with 503
    assert response.status_code == 503
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "AI_SERVICE_ERROR"


@pytest.mark.asyncio
async def test_e2e_correlation_id_in_error_response(
    async_client: AsyncClient,
    api_key_headers: dict[str, str],
) -> None:
    """X-Request-ID appears in error responses."""
    with patch(
        "src.services.chat_service.invoke_agent",
        new_callable=AsyncMock,
        side_effect=Exception("Error"),
    ), _mock_tenant_config():
        response = await async_client.post(
            "/api/v1/chat",
            json={
                "conversationId": "e2e-corr",
                "message": "Test",
                "tenantId": "t-1",
            },
            headers=api_key_headers,
        )

    body = response.json()
    assert body["error"]["requestId"] == "test-request-id"
