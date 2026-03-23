"""Compose router — POST /api/v1/compose endpoint."""

import logging

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from src.dependencies import validate_api_key
from src.models.base_models import BaseResponse, ErrorDetail, ErrorResponse
from src.models.compose_models import ComposeData, ComposeRequest
from src.services.compose_service import compose_message

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/compose")
async def compose(
    request: ComposeRequest,
    request_id: str = Depends(validate_api_key),
) -> BaseResponse[ComposeData]:
    """Compose a personalized care message using AI.

    Requires valid X-API-Key header. Used by the backend auto-flow
    processor to generate feedback and churn reminder messages.
    """
    logger.info(
        "POST /compose: type=%s customer_id=%s tenant_id=%s [request_id=%s]",
        request.type,
        request.customer_id,
        request.tenant_id,
        request_id,
    )

    try:
        message = await compose_message(
            message_type=request.type,
            customer_name=request.context.customer_name,
            service_name=request.context.service_name,
            staff_name=request.context.staff_name,
            days_since_last_visit=request.context.days_since_last_visit,
            request_id=request_id,
        )

        return BaseResponse(
            success=True,
            data=ComposeData(message=message),
        )

    except Exception as e:
        logger.error(
            "Compose failed: %s [request_id=%s]",
            e,
            request_id,
            exc_info=True,
        )
        error_body = ErrorResponse(
            error=ErrorDetail(
                code="COMPOSE_ERROR",
                message="Failed to compose message. Please try again later.",
                request_id=request_id,
            ),
        )
        return JSONResponse(
            status_code=500,
            content=error_body.model_dump(by_alias=True),
        )
