from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db.models import Card, Pair, utcnow
from app.domain import srs


async def create(
    db: AsyncSession,
    pair_id: int,
    direction: str,
    state: str = srs.NEW,
    due_at: datetime | None = None,
) -> Card:
    card = Card(
        pair_id=pair_id,
        direction=direction,
        state=state,
        due_at=due_at if due_at is not None else utcnow(),
    )
    db.add(card)
    await db.flush()
    return card


async def get_for_pair(db: AsyncSession, pair_id: int) -> list[Card]:
    result = await db.execute(select(Card).where(Card.pair_id == pair_id))
    return list(result.scalars().all())


async def get_by_id(db: AsyncSession, card_id: int) -> Card | None:
    result = await db.execute(
        select(Card).options(joinedload(Card.pair)).where(Card.id == card_id)
    )
    return result.scalar_one_or_none()


async def reset_to_new(db: AsyncSession, card: Card, due_at: datetime) -> None:
    card.state = srs.NEW
    card.due_at = due_at
    await db.flush()


async def get_due_cards(
    db: AsyncSession, user_id: int, now: datetime, source: str = "USER"
) -> list[Card]:
    stmt = (
        select(Card)
        .join(Pair, Card.pair_id == Pair.id)
        .where(
            Pair.user_id == user_id,
            Pair.deleted_at.is_(None),
            Pair.source == source,
            Card.state != srs.ARCHIVE,
            Card.due_at <= now,
        )
        .order_by(Card.due_at)
        .options(joinedload(Card.pair))
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_archive_cards(
    db: AsyncSession, user_id: int, source: str = "USER"
) -> list[Card]:
    stmt = (
        select(Card)
        .join(Pair, Card.pair_id == Pair.id)
        .where(
            Pair.user_id == user_id,
            Pair.deleted_at.is_(None),
            Pair.source == source,
            Card.state == srs.ARCHIVE,
        )
        .options(joinedload(Card.pair))
    )
    if source == "VERB":
        # Осиротевшие verb-карточки в архиве больше не подмешиваются в сессии.
        stmt = stmt.where(Pair.is_orphaned.is_(False))
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def count_active_non_archive(
    db: AsyncSession, user_id: int, source: str = "USER"
) -> int:
    stmt = (
        select(func.count(Card.id))
        .join(Pair, Card.pair_id == Pair.id)
        .where(
            Pair.user_id == user_id,
            Pair.deleted_at.is_(None),
            Pair.source == source,
            Card.state != srs.ARCHIVE,
        )
    )
    result = await db.execute(stmt)
    return result.scalar_one()


async def count_archive(
    db: AsyncSession, user_id: int, source: str = "USER"
) -> int:
    stmt = (
        select(func.count(Card.id))
        .join(Pair, Card.pair_id == Pair.id)
        .where(
            Pair.user_id == user_id,
            Pair.deleted_at.is_(None),
            Pair.source == source,
            Card.state == srs.ARCHIVE,
        )
    )
    result = await db.execute(stmt)
    return result.scalar_one()


async def count_due(
    db: AsyncSession, user_id: int, now: datetime, source: str = "USER"
) -> int:
    stmt = (
        select(func.count(Card.id))
        .join(Pair, Card.pair_id == Pair.id)
        .where(
            Pair.user_id == user_id,
            Pair.deleted_at.is_(None),
            Pair.source == source,
            Card.state != srs.ARCHIVE,
            Card.due_at <= now,
        )
    )
    result = await db.execute(stmt)
    return result.scalar_one()
