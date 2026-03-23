"""Tests for compose router — Story 6.3."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_compose_feedback_valid_request(
    async_client: AsyncClient,
    api_key_headers: dict[str, str],
) -> None:
    """POST /api/v1/compose with feedback type returns composed message."""
    mock_message = "Chao Linh, cam on ban da su dung dich vu Gel tay tai tiem."

    with patch(
        "src.routers.compose_router.compose_message",
        new_callable=AsyncMock,
        return_value=mock_message,
    ):
        response = await async_client.post(
            "/api/v1/compose",
            json={
                "type": "feedback",
                "customerId": "cust-001",
                "tenantId": "tenant-001",
                "context": {
                    "customerName": "Linh",
                    "serviceName": "Gel tay",
                    "staffName": "Nga",
                    "daysSinceLastVisit": 0,
                },
            },
            headers=api_key_headers,
        )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["message"] == mock_message


@pytest.mark.asyncio
async def test_compose_churn_reminder_valid_request(
    async_client: AsyncClient,
    api_key_headers: dict[str, str],
) -> None:
    """POST /api/v1/compose with churn_reminder type returns composed message."""
    mock_message = "Chao Mai, da lau khong gap ban. Moi ban quay lai tiem nhe."

    with patch(
        "src.routers.compose_router.compose_message",
        new_callable=AsyncMock,
        return_value=mock_message,
    ):
        response = await async_client.post(
            "/api/v1/compose",
            json={
                "type": "churn_reminder",
                "customerId": "cust-002",
                "tenantId": "tenant-001",
                "context": {
                    "customerName": "Mai",
                    "serviceName": "Cat toc",
                    "staffName": "Hoa",
                    "daysSinceLastVisit": 45,
                },
            },
            headers=api_key_headers,
        )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["message"] == mock_message


@pytest.mark.asyncio
async def test_compose_invalid_api_key(
    async_client: AsyncClient,
    invalid_api_key_headers: dict[str, str],
) -> None:
    """POST /api/v1/compose with invalid API key returns 401."""
    response = await async_client.post(
        "/api/v1/compose",
        json={
            "type": "feedback",
            "customerId": "cust-001",
            "tenantId": "tenant-001",
            "context": {
                "customerName": "Linh",
                "serviceName": "Gel tay",
                "staffName": "Nga",
                "daysSinceLastVisit": 0,
            },
        },
        headers=invalid_api_key_headers,
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_compose_invalid_type_returns_422(
    async_client: AsyncClient,
    api_key_headers: dict[str, str],
) -> None:
    """POST /api/v1/compose with invalid type returns validation error."""
    response = await async_client.post(
        "/api/v1/compose",
        json={
            "type": "invalid_type",
            "customerId": "cust-001",
            "tenantId": "tenant-001",
            "context": {
                "customerName": "Linh",
                "serviceName": "Gel tay",
                "staffName": "Nga",
                "daysSinceLastVisit": 0,
            },
        },
        headers=api_key_headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_compose_ai_failure_returns_500(
    async_client: AsyncClient,
    api_key_headers: dict[str, str],
) -> None:
    """When AI compose fails, returns error response."""
    with patch(
        "src.routers.compose_router.compose_message",
        new_callable=AsyncMock,
        side_effect=Exception("OpenAI API error"),
    ):
        response = await async_client.post(
            "/api/v1/compose",
            json={
                "type": "feedback",
                "customerId": "cust-001",
                "tenantId": "tenant-001",
                "context": {
                    "customerName": "Linh",
                    "serviceName": "Gel tay",
                    "staffName": "Nga",
                    "daysSinceLastVisit": 0,
                },
            },
            headers=api_key_headers,
        )

    assert response.status_code == 500
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "COMPOSE_ERROR"


@pytest.mark.asyncio
async def test_compose_response_uses_camel_case(
    async_client: AsyncClient,
    api_key_headers: dict[str, str],
) -> None:
    """Response body uses camelCase keys."""
    with patch(
        "src.routers.compose_router.compose_message",
        new_callable=AsyncMock,
        return_value="Test message",
    ):
        response = await async_client.post(
            "/api/v1/compose",
            json={
                "type": "feedback",
                "customerId": "cust-001",
                "tenantId": "tenant-001",
                "context": {
                    "customerName": "Test",
                    "serviceName": "Test",
                    "staffName": "Test",
                    "daysSinceLastVisit": 0,
                },
            },
            headers=api_key_headers,
        )

    body = response.json()
    assert "message" in body["data"]
