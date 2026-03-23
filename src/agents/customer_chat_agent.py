"""LangGraph customer chat agent with GPT-4o-mini.

Implements a multi-turn conversation agent using LangGraph StateGraph.
The agent can use tools to call backend API endpoints for customer data,
tenant configuration, and feedback submission.
"""

import logging
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode

from src.agents.prompts.system_prompt import build_system_prompt
from src.config.settings import get_settings
from src.tools.tool_definitions import get_all_tools

logger = logging.getLogger(__name__)

_OPENAI_TIMEOUT = 30
_OPENAI_MAX_RETRIES = 2


def _create_llm() -> ChatOpenAI:
    """Create the ChatOpenAI LLM instance."""
    settings = get_settings()
    return ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.7,
        api_key=settings.openai_api_key,
        timeout=_OPENAI_TIMEOUT,
        max_retries=_OPENAI_MAX_RETRIES,
    )


def _should_continue(state: MessagesState) -> str:
    """Determine whether the agent should call a tool or finish."""
    last_message = state["messages"][-1]
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tools"
    return END


def _build_graph() -> StateGraph:
    """Build the LangGraph StateGraph for the chat agent."""
    tools = get_all_tools()
    llm = _create_llm()
    llm_with_tools = llm.bind_tools(tools)

    async def chatbot(state: MessagesState) -> dict[str, Any]:
        """Process messages through the LLM."""
        response = await llm_with_tools.ainvoke(state["messages"])
        return {"messages": [response]}

    tool_node = ToolNode(tools)

    graph = StateGraph(MessagesState)
    graph.add_node("chatbot", chatbot)
    graph.add_node("tools", tool_node)

    graph.set_entry_point("chatbot")
    graph.add_conditional_edges("chatbot", _should_continue, ["tools", END])
    graph.add_edge("tools", "chatbot")

    return graph


# Compiled graph (module-level singleton)
_compiled_graph = None


def get_compiled_graph():
    """Get or create the compiled LangGraph graph."""
    global _compiled_graph
    if _compiled_graph is None:
        graph = _build_graph()
        _compiled_graph = graph.compile()
    return _compiled_graph


def reset_graph() -> None:
    """Reset the compiled graph. Useful for testing."""
    global _compiled_graph
    _compiled_graph = None


async def invoke_agent(
    message: str,
    conversation_history: list[dict[str, str]] | None = None,
    tenant_config: dict[str, Any] | None = None,
) -> str:
    """Invoke the chat agent with a message and optional conversation history.

    Args:
        message: The user's current message.
        conversation_history: Previous messages as list of
            {"role": "user"|"assistant", "content": "..."}.
        tenant_config: Tenant configuration for prompt customization.

    Returns:
        The agent's reply text.

    Raises:
        Exception: Propagates OpenAI or LangGraph errors after logging.
    """
    logger.info("Invoking agent with message length=%d", len(message))

    system_prompt = build_system_prompt(tenant_config)
    messages: list[SystemMessage | HumanMessage | AIMessage] = [
        SystemMessage(content=system_prompt),
    ]

    # Add conversation history for multi-turn support
    if conversation_history:
        for msg in conversation_history:
            role = msg["role"]
            content = msg["content"]
            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))

    # Add current message
    messages.append(HumanMessage(content=message))

    compiled = get_compiled_graph()
    result = await compiled.ainvoke({"messages": messages})

    # Extract the final AI response
    final_messages = result["messages"]
    for msg in reversed(final_messages):
        if isinstance(msg, AIMessage) and not msg.tool_calls:
            reply = msg.content
            logger.info("Agent replied with length=%d", len(reply))
            return str(reply)

    # Fallback — should not reach here in normal flow
    logger.warning("No AI message found in agent result")
    return "Xin loi, toi khong the xu ly yeu cau cua ban luc nay."
