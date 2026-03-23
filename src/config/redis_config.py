from contextlib import asynccontextmanager
from typing import AsyncGenerator

import redis.asyncio as aioredis

from src.config.settings import get_settings


async def get_redis() -> AsyncGenerator[aioredis.Redis, None]:
    settings = get_settings()
    client = aioredis.from_url(settings.redis_url, decode_responses=True)
    try:
        yield client
    finally:
        await client.aclose()


@asynccontextmanager
async def redis_connection() -> AsyncGenerator[aioredis.Redis, None]:
    settings = get_settings()
    client = aioredis.from_url(settings.redis_url, decode_responses=True)
    try:
        yield client
    finally:
        await client.aclose()
