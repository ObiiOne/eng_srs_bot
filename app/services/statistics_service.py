from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User, utcnow
from app.repositories import cards as cards_repo
from app.repositories import pairs as pairs_repo
from app.repositories import reviews as reviews_repo


async def build_stats(db: AsyncSession, user: User) -> dict:
    pairs_count = await pairs_repo.count_active(db, user.id, source="USER")
    active_cards = await cards_repo.count_active_non_archive(db, user.id, source="USER")
    archive_cards = await cards_repo.count_archive(db, user.id, source="USER")
    due_today = await cards_repo.count_due(db, user.id, utcnow(), source="USER")

    correct = await reviews_repo.count_by_result(db, user.id, True, source="USER")
    errors = await reviews_repo.count_by_result(db, user.id, False, source="USER")
    total = correct + errors
    percent = (correct / total * 100) if total else 0.0

    return {
        "pairs": pairs_count,
        "active_cards": active_cards,
        "archive_cards": archive_cards,
        "due_today": due_today,
        "correct": correct,
        "errors": errors,
        "total": total,
        "percent": percent,
    }
    