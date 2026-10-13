import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

log = logging.getLogger(__name__)


async def ensure_columns(conn: AsyncConnection) -> None:
    """Автомиграция SQLite: добавляет недостающие колонки и индексы."""
    pairs_info = await conn.execute(text("PRAGMA table_info(pairs)"))
    pairs_cols = {row[1] for row in pairs_info.fetchall()}

    if "source" not in pairs_cols:
        log.info("Migration: ALTER pairs ADD source")
        await conn.execute(text(
            "ALTER TABLE pairs ADD COLUMN source VARCHAR(8) NOT NULL DEFAULT 'USER'"
        ))
    if "verb_base" not in pairs_cols:
        log.info("Migration: ALTER pairs ADD verb_base")
        await conn.execute(text(
            "ALTER TABLE pairs ADD COLUMN verb_base VARCHAR(64)"
        ))
    if "is_orphaned" not in pairs_cols:
        log.info("Migration: ALTER pairs ADD is_orphaned")
        await conn.execute(text(
            "ALTER TABLE pairs ADD COLUMN is_orphaned BOOLEAN NOT NULL DEFAULT 0"
        ))

    sessions_info = await conn.execute(text("PRAGMA table_info(study_sessions)"))
    sessions_cols = {row[1] for row in sessions_info.fetchall()}

    if "session_type" not in sessions_cols:
        log.info("Migration: ALTER study_sessions ADD session_type")
        await conn.execute(text(
            "ALTER TABLE study_sessions ADD COLUMN session_type VARCHAR(8) NOT NULL DEFAULT 'USER'"
        ))

    await conn.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_pairs_user_source_deleted "
        "ON pairs(user_id, source, deleted_at)"
    ))
    await conn.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_sessions_user_status_type "
        "ON study_sessions(user_id, status, session_type)"
    ))

