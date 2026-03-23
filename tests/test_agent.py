"""Tests for LangGraph agent — Story 5a.2."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage

from src.agents.customer_chat_agent import invoke_agent, reset_graph
from src.agents.prompts.system_prompt import build_system_prompt


# Reset the graph singleton before each test
@pytest.fixture(autouse=True)
def _reset_agent():
    reset_graph()
    yield
    reset_graph()


def _make_mock_llm(response: AIMessage | Exception):
    """Create a mock ChatOpenAI that returns/raises as specified.

    Uses MagicMock for sync methods (bind_tools) and AsyncMock for
    async methods (ainvoke).
    """
    mock_llm = MagicMock()
    mock_bound = MagicMock()

    if isinstance(response, Exception):
        mock_bound.ainvoke = AsyncMock(side_effect=response)
    else:
        mock_bound.ainvoke = AsyncMock(return_value=response)

    mock_llm.bind_tools.return_value = mock_bound
    return mock_llm, mock_bound


@pytest.mark.asyncio
async def test_invoke_agent_returns_reply() -> None:
    """Agent returns a string reply from the LLM."""
    ai_msg = AIMessage(content="Xin chao! Toi co the giup gi cho ban?")
    mock_llm, mock_bound = _make_mock_llm(ai_msg)

    with patch(
        "src.agents.customer_chat_agent.ChatOpenAI",
        return_value=mock_llm,
    ):
        reply = await invoke_agent(message="Xin chao")

    assert reply == "Xin chao! Toi co the giup gi cho ban?"


@pytest.mark.asyncio
async def test_invoke_agent_with_conversation_history() -> None:
    """Agent receives conversation history for multi-turn support."""
    ai_msg = AIMessage(
        content="Vang, chung toi co dich vu nhuom toc voi gia 200k."
    )
    mock_llm, mock_bound = _make_mock_llm(ai_msg)

    with patch(
        "src.agents.customer_chat_agent.ChatOpenAI",
        return_value=mock_llm,
    ):
        history = [
            {"role": "user", "content": "Tiem co dich vu gi?"},
            {
                "role": "assistant",
                "content": "Chung toi co cat toc, nhuom toc.",
            },
        ]

        reply = await invoke_agent(
            message="Gia nhuom toc bao nhieu?",
            conversation_history=history,
        )

    assert "nhuom toc" in reply
    # LLM called with: system + 2 history + 1 current = 4 messages
    call_args = mock_bound.ainvoke.call_args[0][0]
    assert len(call_args) == 4


@pytest.mark.asyncio
async def test_invoke_agent_openai_timeout() -> None:
    """Agent raises exception when OpenAI times out."""
    mock_llm, _ = _make_mock_llm(
        TimeoutError("OpenAI request timed out")
    )

    with patch(
        "src.agents.customer_chat_agent.ChatOpenAI",
        return_value=mock_llm,
    ):
        with pytest.raises(TimeoutError, match="timed out"):
            await invoke_agent(message="Hello")


@pytest.mark.asyncio
async def test_invoke_agent_openai_api_error() -> None:
    """Agent raises exception when OpenAI returns an API error."""
    mock_llm, _ = _make_mock_llm(
        Exception("API rate limit exceeded")
    )

    with patch(
        "src.agents.customer_chat_agent.ChatOpenAI",
        return_value=mock_llm,
    ):
        with pytest.raises(Exception, match="rate limit"):
            await invoke_agent(message="Hello")


def test_build_system_prompt_returns_string() -> None:
    """build_system_prompt returns a non-empty string."""
    prompt = build_system_prompt()
    assert isinstance(prompt, str)
    assert len(prompt) > 0


def test_build_system_prompt_with_tenant_config() -> None:
    """build_system_prompt accepts tenant_config (Phase 1: ignored)."""
    prompt = build_system_prompt(tenant_config={"name": "Test Salon"})
    assert isinstance(prompt, str)
    assert len(prompt) > 0


def test_build_system_prompt_contains_vietnamese() -> None:
    """System prompt is in Vietnamese."""
    prompt = build_system_prompt()
    assert "tro ly" in prompt or "tiem" in prompt
