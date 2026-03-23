"""Tests for compose service — Story 6.3."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.compose_service import compose_message


@pytest.mark.asyncio
async def test_compose_feedback_message() -> None:
    """compose_message generates feedback text via LLM."""
    mock_response = MagicMock()
    mock_response.content = "Chao Linh, cam on ban da lam Gel tay. Hy vong ban hai long!"

    with patch(
        "src.services.compose_service.ChatOpenAI",
    ) as mock_llm_cls:
        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        mock_llm_cls.return_value = mock_llm

        result = await compose_message(
            message_type="feedback",
            customer_name="Linh",
            service_name="Gel tay",
            staff_name="Nga",
            days_since_last_visit=0,
            request_id="req-001",
        )

    assert result == "Chao Linh, cam on ban da lam Gel tay. Hy vong ban hai long!"
    mock_llm.ainvoke.assert_called_once()


@pytest.mark.asyncio
async def test_compose_churn_reminder_message() -> None:
    """compose_message generates churn reminder text via LLM."""
    mock_response = MagicMock()
    mock_response.content = "Chao Mai, da 45 ngay roi khong gap ban. Moi quay lai nhe!"

    with patch(
        "src.services.compose_service.ChatOpenAI",
    ) as mock_llm_cls:
        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        mock_llm_cls.return_value = mock_llm

        result = await compose_message(
            message_type="churn_reminder",
            customer_name="Mai",
            service_name="Cat toc",
            staff_name="Hoa",
            days_since_last_visit=45,
            request_id="req-002",
        )

    assert "Mai" in result
    mock_llm.ainvoke.assert_called_once()


@pytest.mark.asyncio
async def test_compose_unknown_type_raises_error() -> None:
    """compose_message raises ValueError for unknown message type."""
    with pytest.raises(ValueError, match="Unknown message type"):
        await compose_message(
            message_type="unknown",
            customer_name="Test",
            service_name="Test",
            staff_name="Test",
            days_since_last_visit=0,
            request_id="req-003",
        )


@pytest.mark.asyncio
async def test_compose_propagates_llm_error() -> None:
    """compose_message propagates LLM errors."""
    with patch(
        "src.services.compose_service.ChatOpenAI",
    ) as mock_llm_cls:
        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(side_effect=Exception("OpenAI timeout"))
        mock_llm_cls.return_value = mock_llm

        with pytest.raises(Exception, match="OpenAI timeout"):
            await compose_message(
                message_type="feedback",
                customer_name="Test",
                service_name="Test",
                staff_name="Test",
                days_since_last_visit=0,
                request_id="req-004",
            )
