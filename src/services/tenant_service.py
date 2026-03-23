"""Tenant configuration service with Redis caching.

Fetches tenant configuration from Redis cache first, then falls back
to the backend API on cache miss. Cached results have a 5-minute TTL.
"""

import json
import logging
from typing import Any

from src.config.redis_config import redis_connection
from src.tools.backend_api import call_backend_get

logger = logging.getLogger(__name__)

_CACHE_TTL_SECONDS = 300  # 5 minutes


def _cache_key(tenant_id: str) -> str:
    """Build Redis cache key for tenant AI config."""
    return f"tenant:{tenant_id}:ai-config"


async def get_tenant_config(
    tenant_id: str,
    request_id: str,
) -> dict[str, Any]:
    """Get tenant configuration with Redis cache.

    Flow: Redis cache hit -> return cached.
          Redis cache miss -> fetch from BE API -> cache -> return.

    Args:
        tenant_id: The tenant identifier.
        request_id: Correlation ID for request tracing.

    Returns:
        Tenant configuration dict.
    """
    cache_key = _cache_key(tenant_id)

    # Try Redis cache first
    try:
        async with redis_connection() as redis:
            cached = await redis.get(cache_key)
            if cached is not None:
                logger.info(
                    "Tenant config cache HIT: tenant_id=%s [request_id=%s]",
                    tenant_id,
                    request_id,
                )
                result: dict[str, Any] = json.loads(cached)
                return result
    except Exception as e:
        logger.warning(
            "Redis cache read failed, falling through to BE: %s", e
        )

    # Cache miss — fetch from backend
    logger.info(
        "Tenant config cache MISS: tenant_id=%s [request_id=%s]",
        tenant_id,
        request_id,
    )

    try:
        response = await call_backend_get(
            f"/tenants/{tenant_id}/ai-config",
            request_id,
        )
        config = response.get("data", response)
    except Exception as e:
        logger.error(
            "Failed to fetch tenant config from BE: %s [request_id=%s]",
            e,
            request_id,
        )
        # Return empty config so the agent can still work with defaults
        return {}

    # Cache the result
    try:
        async with redis_connection() as redis:
            await redis.setex(cache_key, _CACHE_TTL_SECONDS, json.dumps(config))
            logger.info(
                "Tenant config cached: tenant_id=%s TTL=%ds [request_id=%s]",
                tenant_id,
                _CACHE_TTL_SECONDS,
                request_id,
            )
    except Exception as e:
        logger.warning("Redis cache write failed: %s", e)

    return config
