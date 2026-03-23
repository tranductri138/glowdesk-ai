import uuid

from fastapi import Header, HTTPException, Request

from src.config.settings import get_settings
from src.models.base_models import ErrorDetail, ErrorResponse


def get_request_id(request: Request) -> str:
    """Extract X-Request-ID from header or generate new UUID."""
    return request.headers.get("x-request-id", str(uuid.uuid4()))


async def validate_api_key(
    request: Request,
    x_api_key: str = Header(alias="X-API-Key"),
) -> str:
    """Validate API key from X-API-Key header. Returns request_id."""
    settings = get_settings()
    request_id = get_request_id(request)

    if x_api_key != settings.ai_service_api_key:
        error_response = ErrorResponse(
            error=ErrorDetail(
                code="AUTH_INVALID_API_KEY",
                message="Invalid API key",
                request_id=request_id,
            )
        )
        raise HTTPException(
            status_code=401,
            detail=error_response.model_dump(by_alias=True),
        )

    return request_id
