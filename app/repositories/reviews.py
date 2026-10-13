from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Card, Pair, Review


async def create(
    db: AsyncSession,
    *,
    user_id: int,
    card_id: int,
    session_id: int | None,
    shown_value: str,
    expected_answer: str,
    user_answer: str,
    is_correct: bool,
    state_before: str,
    state_after: str,
    review_type: str,
) -> Review:
    review = Review(
        user_id=user_id,
        card_id=card_id,
        session_id=session_id,
        shown_value=shown_value,
        expected_answer=expected_answer,
        user_answer=user_answer,
        is_correct=is_correct,
        state_before=state_before,
        state_after=state_after,
        review_type=review_type,
    )
    db.add(review)
    return review


async def count_by_result(
    db: AsyncSession, user_id: int, correct: bool, source: str = "USER"
) -> int:
    stmt = (
        select(func.count(Review.id))
        .join(Card, Review.card_id == Card.id)
        .join(Pair, Card.pair_id == Pair.id)
        .where(
            Review.user_id == user_id,
            Review.is_correct == correct,
            Pair.deleted_at.is_(None),
            Pair.source == source,
        )
    )
    result = await db.execute(stmt)
    return result.scalar_one()


async def get_today_reviewed_card_ids(
    db: AsyncSession,
    user_id: int,
    day_start_utc: datetime,
    source: str = "USER",
) -> list[int]:
    stmt = (
        select(Review.card_id)
        .join(Card, Review.card_id == Card.id)
        .join(Pair, Card.pair_id == Pair.id)
        .where(
            Review.user_id == user_id,
            Review.created_at >= day_start_utc,
            Review.review_type.in_(("REQUIRED", "ARCHIVE")),
            Pair.deleted_at.is_(None),
            Pair.source == source,
        )
        .distinct()
    )
    result = await db.execute(stmt)
    return [row[0] for row in result.all()]
