"""LangChain tool definitions for backend API integration.

These tools allow the LangGraph agent to call backend internal endpoints
for customer data, tenant configuration, and feedback submission.
"""

import contextvars
import logging
from typing import Any

from langchain_core.tools import tool

from src.tools.backend_api import call_backend_get, call_backend_post

logger = logging.getLogger(__name__)

# Thread/task-safe context variable for the current request_id.
# Set by chat_service before invoking the agent so tools can
# forward the correlation ID to backend calls.
_current_request_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    "_current_request_id", default=""
)


def set_request_id(request_id: str) -> None:
    """Set the request ID for the current request context."""
    _current_request_id.set(request_id)


def get_request_id() -> str:
    """Get the current request ID."""
    return _current_request_id.get()


@tool
async def get_customer_info(customer_id: str) -> dict[str, Any]:
    """Lay thong tin khach hang tu he thong CRM.

    Tra ve thong tin ca nhan, lich su dich vu, va ghi chu cua khach hang.

    Args:
        customer_id: Ma dinh danh cua khach hang.
    """
    request_id = get_request_id()
    logger.info(
        "Tool get_customer_info called: customer_id=%s [request_id=%s]",
        customer_id,
        request_id,
    )
    try:
        result = await call_backend_get(
            f"/customers/{customer_id}",
            request_id,
        )
        return result.get("data", result)
    except Exception as e:
        logger.error("get_customer_info failed: %s", e)
        return {"error": f"Khong the lay thong tin khach hang: {e}"}


@tool
async def get_tenant_config(tenant_id: str) -> dict[str, Any]:
    """Lay cau hinh cua tiem (dich vu, gia ca, gio lam viec).

    Tra ve thong tin cau hinh va danh sach dich vu cua tiem.

    Args:
        tenant_id: Ma dinh danh cua tiem.
    """
    request_id = get_request_id()
    logger.info(
        "Tool get_tenant_config called: tenant_id=%s [request_id=%s]",
        tenant_id,
        request_id,
    )
    try:
        result = await call_backend_get(
            f"/tenants/{tenant_id}/config",
            request_id,
        )
        return result.get("data", result)
    except Exception as e:
        logger.error("get_tenant_config failed: %s", e)
        return {"error": f"Khong the lay cau hinh tiem: {e}"}


@tool
async def save_customer_feedback(
    customer_id: str,
    feedback: str,
) -> dict[str, Any]:
    """Luu phan hoi hoac ghi chu cua khach hang vao he thong.

    Su dung khi khach hang gui y kien dong gop, khieu nai,
    hoac bat ky phan hoi nao can ghi lai.

    Args:
        customer_id: Ma dinh danh cua khach hang.
        feedback: Noi dung phan hoi cua khach hang.
    """
    request_id = get_request_id()
    logger.info(
        "Tool save_customer_feedback called: customer_id=%s [request_id=%s]",
        customer_id,
        request_id,
    )
    try:
        result = await call_backend_post(
            f"/customers/{customer_id}/feedback",
            request_id,
            data={"feedback": feedback},
        )
        return result.get("data", result)
    except Exception as e:
        logger.error("save_customer_feedback failed: %s", e)
        return {"error": f"Khong the luu phan hoi: {e}"}


def get_all_tools() -> list:
    """Return list of all LangChain tools for binding to the agent."""
    return [get_customer_info, get_tenant_config, save_customer_feedback]
