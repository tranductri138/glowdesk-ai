"""Pydantic models for chat API request/response."""

from pydantic import Field

from src.models.base_models import CamelModel


class ChatRequest(CamelModel):
    """Incoming chat request from backend."""

    conversation_id: str = Field(..., description="Unique conversation identifier")
    message: str = Field(
        ..., min_length=1, max_length=4000, description="User message text"
    )
    tenant_id: str = Field(..., description="Tenant identifier")


class ChatData(CamelModel):
    """Chat response data payload."""

    reply: str = Field(..., description="AI agent reply text")
    conversation_id: str = Field(..., description="Conversation identifier")
