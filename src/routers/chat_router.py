"""Chat router — POST /api/v1/chat endpoint."""

import logging

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from src.dependencies import validate_api_key
from src.models.base_models import BaseResponse, ErrorDetail, ErrorResponse
from src.models.chat_models import ChatData, ChatRequest
from src.services.chat_service import AIServiceError, process_chat_message

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/chat")
async def chat(
    request: ChatRequest,
    request_id: str = Depends(validate_api_key),
) -> BaseResponse[ChatData]:
    """Process an incoming chat message through the AI agent.

    Requires valid X-API-Key header. Passes through X-Request-ID
    for correlation tracking.
    """
    logger.info(
        "POST /chat: conversation_id=%s tenant_id=%s [request_id=%s]",
        request.conversation_id,
        request.tenant_id,
        request_id,
    )

    try:
        result = await process_chat_message(
            conversation_id=request.conversation_id,
            message=request.message,
            tenant_id=request.tenant_id,
            request_id=request_id,
        )

        return BaseResponse(
            success=True,
            data=ChatData(
                reply=result["reply"],
                conversation_id=result["conversation_id"],
            ),
        )

    except AIServiceError as e:
        logger.error(
            "AI service error: %s [request_id=%s]",
            e,
            request_id,
        )
        error_body = ErrorResponse(
            error=ErrorDetail(
                code="AI_SERVICE_ERROR",
                message=str(e),
                request_id=request_id,
            ),
        )
        return JSONResponse(
            status_code=503,
            content=error_body.model_dump(by_alias=True),
        )

    except Exception:
        logger.error(
            "Unexpected error in chat endpoint [request_id=%s]",
            request_id,
            exc_info=True,
        )
        error_body = ErrorResponse(
            error=ErrorDetail(
                code="INTERNAL_ERROR",
                message="An unexpected error occurred. Please try again later.",
                request_id=request_id,
            ),
        )
        return JSONResponse(
            status_code=500,
            content=error_body.model_dump(by_alias=True),
        )
