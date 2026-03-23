"""Tests for tenant service Redis caching — Story 5a.4."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from src.services.tenant_service import get_tenant_config


@pytest.mark.asyncio
async def test_tenant_config_cache_hit() -> None:
    """When Redis has cached config, return it without calling BE."""
    cached_config = {"id": "tenant-001", "name": "Salon ABC"}
    mock_redis = AsyncMock()
    mock_redis.get.return_value = json.dumps(cached_config)
    mock_redis.aclose = AsyncMock()

    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_redis)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    with patch(
        "src.services.tenant_service.redis_connection",
        return_value=mock_cm,
    ), patch(
        "src.services.tenant_service.call_backend_get",
        new_callable=AsyncMock,
    ) as mock_be:
        result = await get_tenant_config("tenant-001", "req-001")

    assert result["name"] == "Salon ABC"
    mock_be.assert_not_called()


@pytest.mark.asyncio
async def test_tenant_config_cache_miss_fetches_from_be() -> None:
    """When Redis cache is empty, fetch from BE and cache result."""
    be_config = {"id": "tenant-002", "name": "Salon XYZ", "services": []}

    mock_redis = AsyncMock()
    mock_redis.get.return_value = None  # cache miss
    mock_redis.setex = AsyncMock()
    mock_redis.aclose = AsyncMock()

    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_redis)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    with patch(
        "src.services.tenant_service.redis_connection",
        return_value=mock_cm,
    ), patch(
        "src.services.tenant_service.call_backend_get",
        new_callable=AsyncMock,
        return_value={"success": True, "data": be_config},
    ):
        result = await get_tenant_config("tenant-002", "req-002")

    assert result["name"] == "Salon XYZ"
    # Verify it was cached with TTL 300
    mock_redis.setex.assert_called_once()
    args = mock_redis.setex.call_args[0]
    assert args[0] == "tenant:tenant-002:ai-config"
    assert args[1] == 300


@pytest.mark.asyncio
async def test_tenant_config_redis_failure_falls_through() -> None:
    """When Redis is unavailable, fetch from BE without caching."""
    be_config = {"id": "tenant-003", "name": "Salon Fallback"}

    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(side_effect=ConnectionError("Redis down"))
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    with patch(
        "src.services.tenant_service.redis_connection",
        return_value=mock_cm,
    ), patch(
        "src.services.tenant_service.call_backend_get",
        new_callable=AsyncMock,
        return_value={"success": True, "data": be_config},
    ):
        result = await get_tenant_config("tenant-003", "req-003")

    assert result["name"] == "Salon Fallback"


@pytest.mark.asyncio
async def test_tenant_config_be_failure_returns_empty() -> None:
    """When both Redis and BE fail, return empty config."""
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None
    mock_redis.aclose = AsyncMock()

    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_redis)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    with patch(
        "src.services.tenant_service.redis_connection",
        return_value=mock_cm,
    ), patch(
        "src.services.tenant_service.call_backend_get",
        new_callable=AsyncMock,
        side_effect=Exception("BE unreachable"),
    ):
        result = await get_tenant_config("tenant-fail", "req-fail")

    assert result == {}
