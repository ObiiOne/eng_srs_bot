from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Pair, utcnow


async def list_active(
    db: AsyncSession, user_id: int, source: str = "USER"
) -> list[Pair]:
    result = await db.execute(
        select(Pair)
        .where(
            Pair.user_id == user_id,
            Pair.deleted_at.is_(None),
            Pair.source == source,
        )
        .order_by(Pair.id)
    )
    return list(result.scalars().all())


async def get_active(
    db: AsyncSession, user_id: int, pair_id: int, source: str = "USER"
) -> Pair | None:
    result = await db.execute(
        select(Pair).where(
            Pair.id == pair_id,
            Pair.user_id == user_id,
            Pair.deleted_at.is_(None),
            Pair.source == source,
        )
    )
    return result.scalar_one_or_none()


async def find_duplicate(
    db: AsyncSession,
    user_id: int,
    norm_en: str,
    norm_ru: str,
    exclude_id: int | None = None,
    source: str = "USER",
) -> Pair | None:
    stmt = select(Pair).where(
        Pair.user_id == user_id,
        Pair.deleted_at.is_(None),
        Pair.source == source,
        Pair.normalized_english == norm_en,
        Pair.normalized_russian == norm_ru,
    )
    if exclude_id is not None:
        stmt = stmt.where(Pair.id != exclude_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create(
    db: AsyncSession,
    user_id: int,
    english: str,
    russian: str,
    norm_en: str,
    norm_ru: str,
    source: str = "USER",
) -> Pair:
    pair = Pair(
        user_id=user_id,
        source=source,
        english=english,
        russian=russian,
        normalized_english=norm_en,
        normalized_russian=norm_ru,
    )
    db.add(pair)
    await db.flush()
    return pair


async def soft_delete(db: AsyncSession, pair: Pair) -> None:
    pair.deleted_at = utcnow()
    await db.flush()


async def count_active(
    db: AsyncSession, user_id: int, source: str = "USER"
) -> int:
    result = await db.execute(
        select(func.count(Pair.id)).where(
            Pair.user_id == user_id,
            Pair.deleted_at.is_(None),
            Pair.source == source,
        )
    )
    return result.scalar_one()


async def get_verbs_by_base(db: AsyncSession, user_id: int) -> dict[str, Pair]:
    result = await db.execute(
        select(Pair).where(
            Pair.user_id == user_id,
            Pair.source == "VERB",
            Pair.deleted_at.is_(None),
        )
    )
    return {p.verb_base: p for p in result.scalars().all() if p.verb_base}


async def create_verb(
    db: AsyncSession,
    user_id: int,
    base: str,
    english: str,
    russian: str,
    norm_en: str,
    norm_ru: str,
) -> Pair:
    pair = Pair(
        user_id=user_id,
        source="VERB",
        verb_base=base,
        english=english,
        russian=russian,
        normalized_english=norm_en,
        normalized_russian=norm_ru,
    )
    db.add(pair)
    await db.flush()
    return pair
