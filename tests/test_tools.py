"""Tests for LangChain tool definitions — Story 5a.3."""

from unittest.mock import AsyncMock, patch

import pytest

from src.tools.tool_definitions import (
    get_all_tools,
    get_customer_info,
    get_tenant_config,
    save_customer_feedback,
    set_request_id,
)


@pytest.fixture(autouse=True)
def _set_test_request_id():
    set_request_id("test-request-id")
    yield
    set_request_id("")


def test_get_all_tools_returns_three_tools() -> None:
    """Three tools are defined: customer info, tenant config, feedback."""
    tools = get_all_tools()
    assert len(tools) == 3


def test_tools_have_names_and_descriptions() -> None:
    """All tools have name and description for LLM tool binding."""
    tools = get_all_tools()
    for t in tools:
        assert t.name, f"Tool missing name: {t}"
        assert t.description, f"Tool {t.name} missing description"


@pytest.mark.asyncio
async def test_get_customer_info_success() -> None:
    """get_customer_info calls BE and returns customer data."""
    mock_response = {
        "success": True,
        "data": {
            "id": "cust-001",
            "name": "Nguyen Van A",
            "phone": "0901234567",
        },
    }

    with patch(
        "src.tools.tool_definitions.call_backend_get",
        new_callable=AsyncMock,
        return_value=mock_response,
    ) as mock_get:
        result = await get_customer_info.ainvoke({"customer_id": "cust-001"})

    mock_get.assert_called_once_with("/customers/cust-001", "test-request-id")
    assert result["id"] == "cust-001"
    assert result["name"] == "Nguyen Van A"


@pytest.mark.asyncio
async def test_get_customer_info_be_error() -> None:
    """get_customer_info returns error dict when BE call fails."""
    with patch(
        "src.tools.tool_definitions.call_backend_get",
        new_callable=AsyncMock,
        side_effect=Exception("Connection refused"),
    ):
        result = await get_customer_info.ainvoke({"customer_id": "cust-999"})

    assert "error" in result


@pytest.mark.asyncio
async def test_get_tenant_config_success() -> None:
    """get_tenant_config calls BE and returns config data."""
    mock_response = {
        "success": True,
        "data": {
            "id": "tenant-001",
            "name": "Salon ABC",
            "services": ["cat toc", "nhuom toc"],
        },
    }

    with patch(
        "src.tools.tool_definitions.call_backend_get",
        new_callable=AsyncMock,
        return_value=mock_response,
    ) as mock_get:
        result = await get_tenant_config.ainvoke({"tenant_id": "tenant-001"})

    mock_get.assert_called_once_with("/tenants/tenant-001/config", "test-request-id")
    assert result["name"] == "Salon ABC"


@pytest.mark.asyncio
async def test_save_customer_feedback_success() -> None:
    """save_customer_feedback calls BE POST and returns result."""
    mock_response = {
        "success": True,
        "data": {"id": "fb-001", "status": "saved"},
    }

    with patch(
        "src.tools.tool_definitions.call_backend_post",
        new_callable=AsyncMock,
        return_value=mock_response,
    ) as mock_post:
        result = await save_customer_feedback.ainvoke({
            "customer_id": "cust-001",
            "feedback": "Dich vu rat tot!",
        })

    mock_post.assert_called_once_with(
        "/customers/cust-001/feedback",
        "test-request-id",
        data={"feedback": "Dich vu rat tot!"},
    )
    assert result["status"] == "saved"


@pytest.mark.asyncio
async def test_save_customer_feedback_be_error() -> None:
    """save_customer_feedback returns error dict when BE call fails."""
    with patch(
        "src.tools.tool_definitions.call_backend_post",
        new_callable=AsyncMock,
        side_effect=Exception("500 Internal Server Error"),
    ):
        result = await save_customer_feedback.ainvoke({
            "customer_id": "cust-001",
            "feedback": "Test feedback",
        })

    assert "error" in result
