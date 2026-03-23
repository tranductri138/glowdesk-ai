"""Pydantic models for compose API request/response."""

from typing import Literal

from pydantic import Field

from src.models.base_models import CamelModel


class ComposeContext(CamelModel):
    """Context data for message composition."""

    customer_name: str = Field(..., description="Customer display name")
    service_name: str = Field("", description="Service the customer used")
    staff_name: str = Field("", description="Staff who served the customer")
    days_since_last_visit: int = Field(
        0, description="Number of days since customer's last visit"
    )


class ComposeRequest(CamelModel):
    """Incoming compose request from backend auto-flow processor."""

    type: Literal["feedback", "churn_reminder"] = Field(
        ..., description="Message type to compose"
    )
    customer_id: str = Field(..., description="Customer identifier")
    tenant_id: str = Field(..., description="Tenant identifier")
    context: ComposeContext = Field(..., description="Context data for composition")


class ComposeData(CamelModel):
    """Compose response data payload."""

    message: str = Field(..., description="Composed message text")
