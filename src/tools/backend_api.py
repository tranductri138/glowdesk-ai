"""HTTP client for calling backend internal API endpoints.

All calls include X-API-Key and X-Request-ID headers for authentication
and request correlation.
"""

import logging
from typing import Any

import httpx

from src.config.settings import get_settings

logger = logging.getLogger(__name__)

_TIMEOUT = httpx.Timeout(10.0, connect=5.0)


def _build_headers(request_id: str) -> dict[str, str]:
    """Build standard headers for BE internal API calls."""
    settings = get_settings()
    return {
        "X-API-Key": settings.ai_service_api_key,
        "X-Request-ID": request_id,
        "Content-Type": "application/json",
    }


async def call_backend_get(
    path: str,
    request_id: str,
) -> dict[str, Any]:
    """Make a GET request to the backend internal API.

    Args:
        path: URL path relative to the BE internal base URL
              (e.g., "/customers/123").
        request_id: Correlation ID for request tracing.

    Returns:
        Parsed JSON response data.

    Raises:
        httpx.HTTPStatusError: If the response status code indicates an error.
        httpx.ConnectError: If the backend is unreachable.
    """
    settings = get_settings()
    url = f"{settings.glowdesk_be_url}{path}"
    headers = _build_headers(request_id)

    logger.info("BE GET %s [request_id=%s]", url, request_id)

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        result: dict[str, Any] = response.json()
        return result


async def call_backend_post(
    path: str,
    request_id: str,
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Make a POST request to the backend internal API.

    Args:
        path: URL path relative to the BE internal base URL.
        request_id: Correlation ID for request tracing.
        data: JSON body payload.

    Returns:
        Parsed JSON response data.

    Raises:
        httpx.HTTPStatusError: If the response status code indicates an error.
        httpx.ConnectError: If the backend is unreachable.
    """
    settings = get_settings()
    url = f"{settings.glowdesk_be_url}{path}"
    headers = _build_headers(request_id)

    logger.info("BE POST %s [request_id=%s]", url, request_id)

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        response = await client.post(url, headers=headers, json=data or {})
        response.raise_for_status()
        result: dict[str, Any] = response.json()
        return result
