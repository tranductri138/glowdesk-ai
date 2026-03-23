"""Tests for chat router — Story 5a.1."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_chat_endpoint_valid_request(
    async_client: AsyncClient,
    api_key_headers: dict[str, str],
) -> None:
    """POST /api/v1/chat with valid request returns AI reply."""
    mock_reply = "Xin chao! Tiem chung toi co dich vu cat toc va nhuom toc."

    with patch(
        "src.services.chat_service.invoke_agent",
        new_callable=AsyncMock,
        return_value=mock_reply,
    ), patch(
        "src.services.chat_service.get_tenant_config",
        new_callable=AsyncMock,
        return_value={},
    ):
        response = await async_client.post(
            "/api/v1/chat",
            json={
                "conversationId": "conv-001",
                "message": "Xin chao",
                "tenantId": "tenant-001",
            },
            headers=api_key_headers,
        )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["reply"] == mock_reply
    assert body["data"]["conversationId"] == "conv-001"


@pytest.mark.asyncio
async def test_chat_endpoint_invalid_api_key(
    async_client: AsyncClient,
    invalid_api_key_headers: dict[str, str],
) -> None:
    """POST /api/v1/chat with invalid API key returns 401."""
    response = await async_client.post(
        "/api/v1/chat",
        json={
            "conversationId": "conv-001",
            "message": "Xin chao",
            "tenantId": "tenant-001",
        },
        headers=invalid_api_key_headers,
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_chat_endpoint_missing_api_key(
    async_client: AsyncClient,
) -> None:
    """POST /api/v1/chat without X-API-Key returns 422."""
    response = await async_client.post(
        "/api/v1/chat",
        json={
            "conversationId": "conv-001",
            "message": "Xin chao",
            "tenantId": "tenant-001",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_chat_endpoint_correlation_id_pass_through(
    async_client: AsyncClient,
    api_key_headers: dict[str, str],
) -> None:
    """X-Request-ID is forwarded through the chat flow."""
    with patch(
        "src.services.chat_service.invoke_agent",
        new_callable=AsyncMock,
        return_value="Reply",
    ), patch(
        "src.services.chat_service.get_tenant_config",
        new_callable=AsyncMock,
        return_value={},
    ), patch(
        "src.services.chat_service.set_request_id"
    ) as mock_set_req:
        await async_client.post(
            "/api/v1/chat",
            json={
                "conversationId": "conv-002",
                "message": "Test",
                "tenantId": "tenant-001",
            },
            headers=api_key_headers,
        )
        mock_set_req.assert_called_once_with("test-request-id")


@pytest.mark.asyncio
async def test_chat_endpoint_ai_error_returns_error_response(
    async_client: AsyncClient,
    api_key_headers: dict[str, str],
) -> None:
    """When AI agent fails, response still returns structured error."""
    from src.services.chat_service import AIServiceError

    with patch(
        "src.routers.chat_router.process_chat_message",
        new_callable=AsyncMock,
        side_effect=AIServiceError("AI down"),
    ):
        response = await async_client.post(
            "/api/v1/chat",
            json={
                "conversationId": "conv-003",
                "message": "Hello",
                "tenantId": "tenant-001",
            },
            headers=api_key_headers,
        )

    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "AI_SERVICE_ERROR"
    assert body["error"]["requestId"] == "test-request-id"


@pytest.mark.asyncio
async def test_chat_endpoint_empty_message_returns_422(
    async_client: AsyncClient,
    api_key_headers: dict[str, str],
) -> None:
    """Empty message field returns validation error."""
    response = await async_client.post(
        "/api/v1/chat",
        json={
            "conversationId": "conv-001",
            "message": "",
            "tenantId": "tenant-001",
        },
        headers=api_key_headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_chat_response_uses_camel_case(
    async_client: AsyncClient,
    api_key_headers: dict[str, str],
) -> None:
    """Response body uses camelCase keys."""
    with patch(
        "src.services.chat_service.invoke_agent",
        new_callable=AsyncMock,
        return_value="Hi",
    ), patch(
        "src.services.chat_service.get_tenant_config",
        new_callable=AsyncMock,
        return_value={},
    ):
        response = await async_client.post(
            "/api/v1/chat",
            json={
                "conversationId": "conv-camel",
                "message": "Test camelCase",
                "tenantId": "t-1",
            },
            headers=api_key_headers,
        )

    body = response.json()
    assert "conversationId" in body["data"]
    # snake_case should not appear
    assert "conversation_id" not in body["data"]
