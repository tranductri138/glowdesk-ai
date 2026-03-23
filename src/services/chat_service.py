"""Chat service — orchestrates the chat flow.

Wires together: chat_router -> chat_service -> agent
with SQLite persistence and tenant config caching.
"""

import logging
import time
from typing import Any

from src.agents.customer_chat_agent import invoke_agent
from src.db.database import (
    ensure_conversation,
    get_conversation_history,
    get_db,
    save_message,
)
from src.services.tenant_service import get_tenant_config
from src.tools.tool_definitions import set_request_id

logger = logging.getLogger(__name__)


class AIServiceError(Exception):
    """Raised when the AI agent fails to produce a response."""

    def __init__(self, message: str, original_error: Exception | None = None):
        super().__init__(message)
        self.original_error = original_error


async def process_chat_message(
    conversation_id: str,
    message: str,
    tenant_id: str,
    request_id: str,
) -> dict[str, Any]:
    """Process an incoming chat message through the full pipeline.

    Flow:
    1. Set request context (request_id for tool calls)
    2. Load tenant config from Redis/BE
    3. Load conversation history from SQLite
    4. Invoke the LangGraph agent
    5. Save user message + agent reply to SQLite
    6. Return reply

    Args:
        conversation_id: Unique conversation identifier.
        message: User's message text.
        tenant_id: Tenant identifier.
        request_id: Correlation ID for request tracing.

    Returns:
        Dict with 'reply' and 'conversation_id'.

    Raises:
        AIServiceError: If the agent fails to process the message.
    """
    start_time = time.monotonic()
    logger.info(
        "Processing chat: conversation_id=%s tenant_id=%s [request_id=%s]",
        conversation_id,
        tenant_id,
        request_id,
    )

    # Step 1: Set request ID for tool calls
    set_request_id(request_id)

    # Step 2: Load tenant config (Redis cache -> BE API)
    tenant_config = await get_tenant_config(tenant_id, request_id)

    # Step 3: Load conversation history from SQLite
    db = await get_db()
    try:
        await ensure_conversation(db, conversation_id, tenant_id)
        await db.commit()
        history = await get_conversation_history(db, conversation_id)
    except Exception as e:
        logger.error("Failed to load conversation history: %s", e)
        history = []
    finally:
        await db.close()

    # Step 4: Invoke the agent
    try:
        reply = await invoke_agent(
            message=message,
            conversation_history=history,
            tenant_config=tenant_config,
        )
    except Exception as e:
        elapsed = time.monotonic() - start_time
        logger.error(
            "Agent invocation failed after %.2fs: %s [request_id=%s]",
            elapsed,
            e,
            request_id,
        )
        raise AIServiceError(
            "AI service is temporarily unavailable. Please try again later.",
            original_error=e,
        ) from e

    # Step 5: Save messages to SQLite
    db = await get_db()
    try:
        await save_message(db, conversation_id, "user", message)
        await save_message(db, conversation_id, "assistant", reply)
        await db.commit()
    except Exception as e:
        logger.error("Failed to save messages: %s [request_id=%s]", e, request_id)
        # Do not fail the response if saving fails
    finally:
        await db.close()

    elapsed = time.monotonic() - start_time
    logger.info(
        "Chat processed in %.2fs: conversation_id=%s [request_id=%s]",
        elapsed,
        conversation_id,
        request_id,
    )

    return {
        "reply": reply,
        "conversation_id": conversation_id,
    }
