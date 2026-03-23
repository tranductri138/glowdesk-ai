import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from src.db.database import init_db
from src.routers.chat_router import router as chat_router
from src.routers.compose_router import router as compose_router
from src.routers.health_router import router as health_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [glowdesk-ai] %(message)s",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: initialize DB on startup."""
    logger.info("Starting GlowDesk AI Service...")
    await init_db()
    logger.info("GlowDesk AI Service ready")
    yield
    logger.info("Shutting down GlowDesk AI Service")


app = FastAPI(
    title="GlowDesk AI Service",
    description="AI service for GlowDesk CRM",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
app.include_router(compose_router, prefix="/api/v1")
