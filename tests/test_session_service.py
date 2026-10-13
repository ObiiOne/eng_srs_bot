from datetime import timedelta

import pytest

from app.db.models import utcnow
from app.repositories import users as users_repo
from app.services import pair_service, session_service


@pytest.mark.asyncio
async def test_build_session_min_size(db):
    user = await users_repo.get_or_create(db, 1, "Europe/Moscow")
    await db.commit()
    await pair_service.create_pair(db, user, "a", "а")
    await pair_service.create_pair(db, user, "b", "б")

    session = await session_service.build_session(db, user)
    assert session is not None
    from app.repositories import sessions as sessions_repo

    total = await sessions_repo.count_total(db, session.id)
    assert total == 4  # 4 обязательные карточки (2 пары × 2 направления)


@pytest.mark.asyncio
async def test_wrong_answer_srs_drop(db):
    user = await users_repo.get_or_create(db, 1, "Europe/Moscow")
    await db.commit()
    await pair_service.create_pair(db, user, "warehouse", "склад")

    session = await session_service.build_session(db, user)
    from app.repositories import sessions as sessions_repo

    sc = await sessions_repo.next_pending(db, session.id)
    card = sc.card
    card.state = "D7"
    await db.commit()

    result = await session_service.process_answer(db, user, session, "совсем другое")
    assert result["is_correct"] is False
    await db.refresh(card)
    assert card.state == "D3"


@pytest.mark.asyncio
async def test_no_cards_returns_none(db):
    user = await users_repo.get_or_create(db, 1, "Europe/Moscow")
    await db.commit()
    session = await session_service.build_session(db, user)
    assert session is None

