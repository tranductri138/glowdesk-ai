"""Compose service — generates personalized care messages using LLM.

Uses a simple LLM call (not a full agent) to compose feedback or
churn reminder messages in natural Vietnamese.
"""

import logging
import time

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from src.config.settings import get_settings

logger = logging.getLogger(__name__)

_COMPOSE_SYSTEM_PROMPT = (
    "Ban la tro ly ao cua mot tiem lam dep. "
    "Nhiem vu cua ban la viet tin nhan cham soc khach hang bang tieng Viet tu nhien, "
    "than thien, va chuyen nghiep. "
    "Tin nhan phai ngan gon (1-3 cau), khong co emoji qua nhieu, "
    "va phu hop voi van hoa Viet Nam. "
    "Chi tra ve noi dung tin nhan, khong them gi khac."
)

_FEEDBACK_PROMPT_TEMPLATE = (
    "Viet tin nhan cam on khach hang sau khi su dung dich vu.\n"
    "Thong tin:\n"
    "- Ten khach hang: {customer_name}\n"
    "- Dich vu da lam: {service_name}\n"
    "- Tho phuc vu: {staff_name}\n"
    "Tin nhan can: cam on, hoi thong tin ve trai nghiem, "
    "va moi khach quay lai."
)

_CHURN_REMINDER_PROMPT_TEMPLATE = (
    "Viet tin nhan nhac nho khach hang da lau khong quay lai tiem.\n"
    "Thong tin:\n"
    "- Ten khach hang: {customer_name}\n"
    "- Dich vu lan cuoi: {service_name}\n"
    "- Tho phuc vu lan cuoi: {staff_name}\n"
    "- So ngay tu lan cuoi: {days_since_last_visit}\n"
    "Tin nhan can: the hien su quan tam, nhac ve dich vu cu, "
    "va moi khach quay lai voi uu dai moi."
)


async def compose_message(
    message_type: str,
    customer_name: str,
    service_name: str,
    staff_name: str,
    days_since_last_visit: int,
    request_id: str,
) -> str:
    """Compose a personalized care message using the LLM.

    Args:
        message_type: "feedback" or "churn_reminder".
        customer_name: Customer's display name.
        service_name: Service the customer used.
        staff_name: Staff who served the customer.
        days_since_last_visit: Days since last visit (for churn).
        request_id: Correlation ID for tracing.

    Returns:
        The composed message text.

    Raises:
        Exception: Propagates LLM errors for the caller to handle.
    """
    start_time = time.monotonic()
    logger.info(
        "Composing %s message for customer '%s' [request_id=%s]",
        message_type,
        customer_name,
        request_id,
    )

    if message_type == "feedback":
        prompt = _FEEDBACK_PROMPT_TEMPLATE.format(
            customer_name=customer_name,
            service_name=service_name or "dich vu",
            staff_name=staff_name or "nhan vien",
        )
    elif message_type == "churn_reminder":
        prompt = _CHURN_REMINDER_PROMPT_TEMPLATE.format(
            customer_name=customer_name,
            service_name=service_name or "dich vu",
            staff_name=staff_name or "nhan vien",
            days_since_last_visit=days_since_last_visit,
        )
    else:
        raise ValueError(f"Unknown message type: {message_type}")

    settings = get_settings()
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.8,
        api_key=settings.openai_api_key,
        timeout=15,
        max_retries=1,
    )

    messages = [
        SystemMessage(content=_COMPOSE_SYSTEM_PROMPT),
        HumanMessage(content=prompt),
    ]

    response = await llm.ainvoke(messages)
    composed = str(response.content).strip()

    elapsed = time.monotonic() - start_time
    logger.info(
        "Composed %s message (len=%d) in %.2fs [request_id=%s]",
        message_type,
        len(composed),
        elapsed,
        request_id,
    )

    return composed
