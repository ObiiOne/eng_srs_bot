from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User, utcnow
from app.domain import srs
from app.domain.normalization import normalize, normalize_verb
from app.domain.verbs import VerbEntry
from app.repositories import cards as cards_repo
from app.repositories import pairs as pairs_repo
from app.repositories import reviews as reviews_repo


async def sync_verbs(db: AsyncSession, user: User, entries: list[VerbEntry]) -> None:
    now = utcnow()
    existing = await pairs_repo.get_verbs_by_base(db, user.id)
    json_bases: set[str] = set()

    for v in entries:
        json_bases.add(v.base)
        english = v.english_display
        norm_en = normalize_verb(english)
        norm_ru = normalize(v.ru)

        pair = existing.get(v.base)
        if pair is None:
            pair = await pairs_repo.create_verb(
                db, user.id, v.base, english, v.ru, norm_en, norm_ru
            )
            await cards_repo.create(db, pair.id, "EN_RU", srs.NEW, now)
            await cards_repo.create(db, pair.id, "RU_EN", srs.NEW, now)
        else:
            pair.english = english
            pair.normalized_english = norm_en
            pair.russian = v.ru
            pair.normalized_russian = norm_ru
            pair.is_orphaned = False
            pair.updated_at = now

    for base, pair in existing.items():
        if base not in json_bases:
            pair.is_orphaned = True

    await db.commit()


async def build_verb_stats(db: AsyncSession, user: User) -> dict:
    pairs_count = await pairs_repo.count_active(db, user.id, source="VERB")
    active_cards = await cards_repo.count_active_non_archive(db, user.id, source="VERB")
    archive_cards = await cards_repo.count_archive(db, user.id, source="VERB")
    due_today = await cards_repo.count_due(db, user.id, utcnow(), source="VERB")
    correct = await reviews_repo.count_by_result(db, user.id, True, source="VERB")
    errors = await reviews_repo.count_by_result(db, user.id, False, source="VERB")
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

