import pytest

from app.repositories import users as users_repo
from app.services import pair_service
from app.services.pair_service import PairDuplicateError


@pytest.mark.asyncio
async def test_create_pair_creates_two_cards(db):
    user = await users_repo.get_or_create(db, 1, "Europe/Moscow")
    await db.commit()

    pair = await pair_service.create_pair(db, user, "warehouse", "склад")

    from app.repositories import cards as cards_repo

    cards = await cards_repo.get_for_pair(db, pair.id)
    assert len(cards) == 2
    assert {c.direction for c in cards} == {"EN_RU", "RU_EN"}
    assert all(c.state == "NEW" for c in cards)


@pytest.mark.asyncio
async def test_duplicate_rejected(db):
    user = await users_repo.get_or_create(db, 1, "Europe/Moscow")
    await db.commit()

    await pair_service.create_pair(db, user, "warehouse", "склад")
    with pytest.raises(PairDuplicateError):
        await pair_service.create_pair(db, user, "  WAREHOUSE ", "СКЛАД")


@pytest.mark.asyncio
async def test_edit_resets_cards(db):
    from app.repositories import cards as cards_repo

    user = await users_repo.get_or_create(db, 1, "Europe/Moscow")
    await db.commit()

    pair = await pair_service.create_pair(db, user, "warehouse", "склад")
    cards = await cards_repo.get_for_pair(db, pair.id)
    for c in cards:
        c.state = "D7"
    await db.commit()

    await pair_service.update_pair(db, user, pair.id, "warehouse", "хранилище")

    cards = await cards_repo.get_for_pair(db, pair.id)
    assert all(c.state == "NEW" for c in cards)
