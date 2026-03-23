"""SQLite database management for conversation persistence."""

import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite

from src.config.settings import get_settings

logger = logging.getLogger(__name__)

_CREATE_CONVERSATIONS_TABLE = """
CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

_CREATE_MESSAGES_TABLE = """
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);
"""

_CREATE_MESSAGES_INDEX = """
CREATE INDEX IF NOT EXISTS idx_messages_conversation_id
ON messages(conversation_id);
"""


async def get_db_path() -> str:
    """Get the SQLite database file path, ensuring the directory exists."""
    settings = get_settings()
    db_path = settings.sqlite_db_path
    os.makedirs(Path(db_path).parent, exist_ok=True)
    return db_path


async def init_db() -> None:
    """Initialize database and create tables."""
    db_path = await get_db_path()
    async with aiosqlite.connect(db_path) as db:
        await db.execute(_CREATE_CONVERSATIONS_TABLE)
        await db.execute(_CREATE_MESSAGES_TABLE)
        await db.execute(_CREATE_MESSAGES_INDEX)
        await db.commit()
    logger.info("SQLite database initialized at %s", db_path)


async def get_db() -> aiosqlite.Connection:
    """Get a new database connection."""
    db_path = await get_db_path()
    db = await aiosqlite.connect(db_path)
    db.row_factory = aiosqlite.Row
    return db


async def ensure_conversation(
    db: aiosqlite.Connection,
    conversation_id: str,
    tenant_id: str,
) -> None:
    """Create conversation record if it does not exist."""
    await db.execute(
        "INSERT OR IGNORE INTO conversations (id, tenant_id) VALUES (?, ?)",
        (conversation_id, tenant_id),
    )


async def save_message(
    db: aiosqlite.Connection,
    conversation_id: str,
    role: str,
    content: str,
) -> None:
    """Save a single message to the messages table."""
    now = datetime.now(timezone.utc).isoformat()
    await db.execute(
        "INSERT INTO messages (conversation_id, role, content, created_at) "
        "VALUES (?, ?, ?, ?)",
        (conversation_id, role, content, now),
    )


async def get_conversation_history(
    db: aiosqlite.Connection,
    conversation_id: str,
    limit: int = 50,
) -> list[dict[str, str]]:
    """Retrieve conversation messages ordered by creation time.

    Returns list of dicts with keys: role, content.
    """
    cursor = await db.execute(
        "SELECT role, content FROM messages "
        "WHERE conversation_id = ? ORDER BY created_at ASC LIMIT ?",
        (conversation_id, limit),
    )
    rows = await cursor.fetchall()
    return [{"role": row["role"], "content": row["content"]} for row in rows]
