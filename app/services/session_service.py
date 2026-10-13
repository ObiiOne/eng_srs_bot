import random
from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Card, StudySession, User, utcnow
from app.domain import srs
from app.domain.normalization import answers_match, answers_match_verb
from app.repositories import cards as cards_repo
from app.repositories import reviews as reviews_repo
from app.repositories import sessions as sessions_repo

MIN_SESSION_SIZE = 5
DIRECTIONS = ("EN_RU", "RU_EN")


def end_of_day_utc(tz_name: str, now_naive_utc: datetime) -> datetime:
    tz = ZoneInfo(tz_name)
    aware = now_naive_utc.replace(tzinfo=timezone.utc)
    local = aware.astimezone(tz)
    end_local = datetime.combine(local.date(), time(23, 59, 59, 999999), tzinfo=tz)
    return end_local.astimezone(timezone.utc).replace(tzinfo=None)


def start_of_day_utc(tz_name: str, now_naive_utc: datetime) -> datetime:
    tz = ZoneInfo(tz_name)
    aware = now_naive_utc.replace(tzinfo=timezone.utc)
    local = aware.astimezone(tz)
    start_local = datetime.combine(local.date(), time(0, 0, 0), tzinfo=tz)
    return start_local.astimezone(timezone.utc).replace(tzinfo=None)


def question_for(card: Card) -> tuple[str, str, str]:
    """Возвращает (shown_value, expected_answer, направление-метка)."""
    pair = card.pair
    if card.direction == "EN_RU":
        return pair.english, pair.russian, "EN → RU"
    return pair.russian, pair.english, "RU → EN"


async def get_active_session(
    db: AsyncSession, user: User, session_type: str = "USER"
) -> StudySession | None:
    active = await sessions_repo.get_active(db, user.id, session_type)
    if active is None:
        return None
    if active.expires_at <= utcnow():
        active.status = "EXPIRED"
        active.completed_at = utcnow()
        await db.commit()
        return None
    return active


async def get_any_active_session(db: AsyncSession, user: User) -> StudySession | None:
    for st in ("USER", "VERB"):
        s = await get_active_session(db, user, st)
        if s is not None:
            return s
    return None


async def build_session(
    db: AsyncSession, user: User, session_type: str = "USER"
) -> StudySession | None:
    source = session_type
    now = utcnow()
    required = await cards_repo.get_due_cards(db, user.id, now, source=source)
    archive = await cards_repo.get_archive_cards(db, user.id, source=source)

    selected: list[tuple[Card, str]] = []
    selected_ids: set[int] = set()

    for card in required:
        selected.append((card, "REQUIRED"))
        selected_ids.add(card.id)

    # минимум одна архивная EN_RU и одна RU_EN
    for direction in DIRECTIONS:
        pool = [c for c in archive if c.direction == direction and c.id not in selected_ids]
        random.shuffle(pool)
        if pool:
            selected.append((pool[0], "ARCHIVE"))
            selected_ids.add(pool[0].id)

    # добор до MIN_SESSION_SIZE, если обязательных меньше
    if len(required) < MIN_SESSION_SIZE:
        pool = [c for c in archive if c.id not in selected_ids]
        random.shuffle(pool)
        for card in pool:
            if len(selected) >= MIN_SESSION_SIZE:
                break
            selected.append((card, "ARCHIVE"))
            selected_ids.add(card.id)

    if not selected:
        return None

    session = StudySession(
        user_id=user.id,
        session_type=session_type,
        status="ACTIVE",
        started_at=now,
        expires_at=end_of_day_utc(user.timezone, now),
    )
    db.add(session)
    await db.flush()

    random.shuffle(selected)
    for position, (card, review_type) in enumerate(selected):
        await sessions_repo.add_card(db, session.id, card.id, position, review_type)

    await db.commit()
    return session


async def interrupt_session(db: AsyncSession, session: StudySession) -> None:
    session.status = "INTERRUPTED"
    session.completed_at = utcnow()
    await db.commit()


async def session_progress(db: AsyncSession, session: StudySession) -> tuple[int, int]:
    total = await sessions_repo.count_total(db, session.id)
    answered = await sessions_repo.count_answered(db, session.id)
    return answered, total


async def process_answer(
    db: AsyncSession, user: User, session: StudySession, user_answer: str
) -> dict:
    sc = await sessions_repo.next_pending(db, session.id)
    if sc is None:
        return {"done": True, "finished": True}

    card = sc.card
    shown, expected, _ = question_for(card)

    if card.pair is not None and card.pair.source == "VERB":
        is_correct = answers_match_verb(user_answer, expected)
    else:
        is_correct = answers_match(user_answer, expected)

    state_before = card.state
    new_state = srs.next_state(state_before, is_correct)
    now = utcnow()
    card.state = new_state
    card.due_at = srs.next_due(state_before, new_state, now)

    await reviews_repo.create(
        db,
        user_id=user.id,
        card_id=card.id,
        session_id=session.id,
        shown_value=shown,
        expected_answer=expected,
        user_answer=user_answer,
        is_correct=is_correct,
        state_before=state_before,
        state_after=new_state,
        review_type=sc.review_type,
    )
    sc.status = "ANSWERED"

    remaining = await sessions_repo.count_pending(db, session.id)
    finished = remaining == 0
    if finished:
        session.status = "COMPLETED"
        session.completed_at = now

    await db.commit()

    return {
        "done": False,
        "finished": finished,
        "is_correct": is_correct,
        "shown": shown,
        "expected": expected,
        "state_before": state_before,
        "state_after": new_state,
        "session_type": session.session_type,
    }


async def process_early_answer(
    db: AsyncSession, user: User, card: Card, user_answer: str
) -> dict:
    shown, expected, _ = question_for(card)
    if card.pair is not None and card.pair.source == "VERB":
        is_correct = answers_match_verb(user_answer, expected)
    else:
        is_correct = answers_match(user_answer, expected)
    await reviews_repo.create(
        db,
        user_id=user.id,
        card_id=card.id,
        session_id=None,
        shown_value=shown,
        expected_answer=expected,
        user_answer=user_answer,
        is_correct=is_correct,
        state_before=card.state,
        state_after=card.state,
        review_type="EARLY",
    )
    await db.commit()
    return {"is_correct": is_correct, "shown": shown, "expected": expected}


async def get_early_review_cards(
    db: AsyncSession, user: User, source: str = "USER"
) -> list[Card]:
    day_start = start_of_day_utc(user.timezone, utcnow())
    ids = await reviews_repo.get_today_reviewed_card_ids(
        db, user.id, day_start, source=source
    )
    if not ids:
        return []
    cards: list[Card] = []
    for cid in ids:
        card = await cards_repo.get_by_id(db, cid)
        if card and card.pair and card.pair.deleted_at is None:
            cards.append(card)
    random.shuffle(cards)
    return cards
