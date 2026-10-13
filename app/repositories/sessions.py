from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db.models import Card, SessionCard, StudySession


async def get_active(
    db: AsyncSession, user_id: int, session_type: str = "USER"
) -> StudySession | None:
    stmt = (
        select(StudySession)
        .where(
            StudySession.user_id == user_id,
            StudySession.status == "ACTIVE",
            StudySession.session_type == session_type,
        )
        .order_by(StudySession.id.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_by_id(db: AsyncSession, session_id: int) -> StudySession | None:
    result = await db.execute(select(StudySession).where(StudySession.id == session_id))
    return result.scalar_one_or_none()


async def add_card(
    db: AsyncSession,
    session_id: int,
    card_id: int,
    position: int,
    review_type: str,
) -> SessionCard:
    sc = SessionCard(
        session_id=session_id,
        card_id=card_id,
        position=position,
        review_type=review_type,
        status="PENDING",
    )
    db.add(sc)
    return sc


async def next_pending(db: AsyncSession, session_id: int) -> SessionCard | None:
    stmt = (
        select(SessionCard)
        .options(joinedload(SessionCard.card).joinedload(Card.pair))
        .where(SessionCard.session_id == session_id, SessionCard.status == "PENDING")
        .order_by(SessionCard.position)
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def count_total(db: AsyncSession, session_id: int) -> int:
    result = await db.execute(
        select(func.count(SessionCard.id)).where(SessionCard.session_id == session_id)
    )
    return result.scalar_one()


async def count_pending(db: AsyncSession, session_id: int) -> int:
    result = await db.execute(
        select(func.count(SessionCard.id)).where(
            SessionCard.session_id == session_id, SessionCard.status == "PENDING"
        )
    )
    return result.scalar_one()


async def count_answered(db: AsyncSession, session_id: int) -> int:
    result = await db.execute(
        select(func.count(SessionCard.id)).where(
            SessionCard.session_id == session_id, SessionCard.status == "ANSWERED"
        )
    )
    return result.scalar_one()
