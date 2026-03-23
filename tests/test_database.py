"""Tests for SQLite database CRUD — Story 5a.4."""

import os

import aiosqlite
import pytest

from src.db.database import (
    ensure_conversation,
    get_conversation_history,
    init_db,
    save_message,
)

_TEST_DB = "./data/test-crud.db"


@pytest.fixture(autouse=True)
async def _setup_test_db():
    """Set up a clean test database for each test."""
    os.environ["SQLITE_DB_PATH"] = _TEST_DB
    # Reset the settings cache so the new path is picked up
    import src.config.settings as settings_mod
    settings_mod._settings = None

    await init_db()
    yield

    # Clean up
    if os.path.exists(_TEST_DB):
        os.remove(_TEST_DB)
    settings_mod._settings = None


async def _get_test_db() -> aiosqlite.Connection:
    db = await aiosqlite.connect(_TEST_DB)
    db.row_factory = aiosqlite.Row
    return db


@pytest.mark.asyncio
async def test_init_db_creates_tables() -> None:
    """init_db creates conversations and messages tables."""
    db = await _get_test_db()
    try:
        cursor = await db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = [row["name"] for row in await cursor.fetchall()]
        assert "conversations" in tables
        assert "messages" in tables
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_ensure_conversation_creates_record() -> None:
    """ensure_conversation inserts a new conversation row."""
    db = await _get_test_db()
    try:
        await ensure_conversation(db, "conv-100", "tenant-100")
        await db.commit()

        cursor = await db.execute(
            "SELECT id, tenant_id FROM conversations WHERE id = ?",
            ("conv-100",),
        )
        row = await cursor.fetchone()
        assert row is not None
        assert row["id"] == "conv-100"
        assert row["tenant_id"] == "tenant-100"
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_ensure_conversation_idempotent() -> None:
    """Calling ensure_conversation twice does not raise."""
    db = await _get_test_db()
    try:
        await ensure_conversation(db, "conv-dup", "tenant-001")
        await ensure_conversation(db, "conv-dup", "tenant-001")
        await db.commit()

        cursor = await db.execute(
            "SELECT COUNT(*) as cnt FROM conversations WHERE id = ?",
            ("conv-dup",),
        )
        row = await cursor.fetchone()
        assert row["cnt"] == 1
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_save_and_get_messages() -> None:
    """save_message and get_conversation_history work together."""
    db = await _get_test_db()
    try:
        await ensure_conversation(db, "conv-msg", "tenant-001")
        await save_message(db, "conv-msg", "user", "Xin chao")
        await save_message(db, "conv-msg", "assistant", "Chao ban!")
        await save_message(db, "conv-msg", "user", "Gia dich vu?")
        await db.commit()

        history = await get_conversation_history(db, "conv-msg")

        assert len(history) == 3
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "Xin chao"
        assert history[1]["role"] == "assistant"
        assert history[1]["content"] == "Chao ban!"
        assert history[2]["role"] == "user"
        assert history[2]["content"] == "Gia dich vu?"
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_get_conversation_history_empty() -> None:
    """get_conversation_history returns empty list for unknown conversation."""
    db = await _get_test_db()
    try:
        history = await get_conversation_history(db, "conv-nonexistent")
        assert history == []
    finally:
        await db.close()


@pytest.mark.asyncio
async def test_get_conversation_history_respects_limit() -> None:
    """get_conversation_history respects the limit parameter."""
    db = await _get_test_db()
    try:
        await ensure_conversation(db, "conv-limit", "tenant-001")
        for i in range(10):
            await save_message(db, "conv-limit", "user", f"Message {i}")
        await db.commit()

        history = await get_conversation_history(db, "conv-limit", limit=5)
        assert len(history) == 5
    finally:
        await db.close()
