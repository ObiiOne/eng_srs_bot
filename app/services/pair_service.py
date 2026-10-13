from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Pair, User, utcnow
from app.domain import srs
from app.domain.normalization import normalize
from app.repositories import cards as cards_repo
from app.repositories import pairs as pairs_repo


class PairValidationError(Exception):
    pass


class PairDuplicateError(Exception):
    pass


async def create_pair(db: AsyncSession, user: User, english: str, russian: str) -> Pair:
    en = (english or "").strip()
    ru = (russian or "").strip()
    norm_en = normalize(en)
    norm_ru = normalize(ru)

    if not norm_en or not norm_ru:
        raise PairValidationError("Пустое значение не принимается.")

    existing = await pairs_repo.find_duplicate(db, user.id, norm_en, norm_ru)
    if existing is not None:
        raise PairDuplicateError("Такая пара уже существует.")

    pair = await pairs_repo.create(db, user.id, en, ru, norm_en, norm_ru)
    now = utcnow()
    await cards_repo.create(db, pair.id, "EN_RU", srs.NEW, now)
    await cards_repo.create(db, pair.id, "RU_EN", srs.NEW, now)
    await db.commit()
    return pair


async def update_pair(
    db: AsyncSession, user: User, pair_id: int, english: str, russian: str
) -> Pair:
    pair = await pairs_repo.get_active(db, user.id, pair_id)
    if pair is None:
        raise PairValidationError("Пара не найдена.")

    en = (english or "").strip()
    ru = (russian or "").strip()
    norm_en = normalize(en)
    norm_ru = normalize(ru)

    if not norm_en or not norm_ru:
        raise PairValidationError("Пустое значение не принимается.")

    duplicate = await pairs_repo.find_duplicate(db, user.id, norm_en, norm_ru, exclude_id=pair.id)
    if duplicate is not None:
        raise PairDuplicateError("Такая пара уже существует.")

    pair.english = en
    pair.russian = ru
    pair.normalized_english = norm_en
    pair.normalized_russian = norm_ru
    pair.updated_at = utcnow()

    now = utcnow()
    for card in await cards_repo.get_for_pair(db, pair.id):
        await cards_repo.reset_to_new(db, card, now)

    await db.commit()
    return pair


async def delete_pair(db: AsyncSession, user: User, pair_id: int) -> bool:
    pair = await pairs_repo.get_active(db, user.id, pair_id)
    if pair is None:
        return False
    await pairs_repo.soft_delete(db, pair)
    await db.commit()
    return True


async def list_pairs(db: AsyncSession, user: User) -> list[Pair]:
    return await pairs_repo.list_active(db, user.id)


async def get_pair(db: AsyncSession, user: User, pair_id: int) -> Pair | None:
    return await pairs_repo.get_active(db, user.id, pair_id)
