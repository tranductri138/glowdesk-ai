from fastapi import APIRouter

from src.models.base_models import BaseResponse

router = APIRouter()


@router.get("/health", response_model=BaseResponse[dict])
async def health_check() -> BaseResponse[dict]:
    return BaseResponse(success=True, data={"status": "healthy"})
