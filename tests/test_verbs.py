import json

import pytest

from app.domain.normalization import answers_match_verb, normalize_verb
from app.domain.verbs import VerbConfigError, VerbEntry, load_verbs
from app.repositories import users as users_repo
from app.repositories import pairs as pairs_repo
from app.services import pair_service, session_service, verb_service


# --- normalization ---

def test_verb_normalization_separators():
    assert normalize_verb("do, did, done") == "do did done"
    assert normalize_verb("do/did/done") == "do did done"
    assert normalize_verb("do.did.done") == "do did done"
    assert normalize_verb("Do;Did;Done") == "do did done"
    assert normalize_verb("do — did — done") == "do did done"
    assert normalize_verb("  DO  DID   DONE  ") == "do did done"


def test_verb_order_matters():
    assert not answers_match_verb("did do done", "do did done")


def test_verb_typos_rejected():
    assert not answers_match_verb("doing did done", "do did done")


def test_verb_matches_correct_order():
    assert answers_match_verb("do did done", "do did done")
    assert answers_match_verb("do, did, done", "do did done")


# --- loader ---

def test_load_valid(tmp_path):
    p = tmp_path / "v.json"
    p.write_text(json.dumps([
        {"base": "go", "past": "went", "pp": "gone", "ru": "идти"},
    ]), encoding="utf-8")
    entries = load_verbs(str(p))
    assert len(entries) == 1
    assert entries[0].english_display == "go went gone"


def test_load_duplicate_base(tmp_path):
    p = tmp_path / "v.json"
    p.write_text(json.dumps([
        {"base": "go", "past": "went", "pp": "gone", "ru": "идти"},
        {"base": "go", "past": "went", "pp": "gone", "ru": "ехать"},
    ]), encoding="utf-8")
    with pytest.raises(VerbConfigError):
        load_verbs(str(p))


def test_load_broken_json(tmp_path):
    p = tmp_path / "v.json"
    p.write_text("{not json", encoding="utf-8")
    with pytest.raises(VerbConfigError):
        load_verbs(str(p))


def test_load_missing_field(tmp_path):
    p = tmp_path / "v.json"
    p.write_text(json.dumps([{"base": "go", "past": "went", "ru": "идти"}]), encoding="utf-8")
    with pytest.raises(VerbConfigError):
        load_verbs(str(p))


# --- sync ---

@pytest.mark.asyncio
async def test_sync_verbs_idempotent(db):
    user = await users_repo.get_or_create(db, 1, "Europe/Moscow")
    await db.commit()

    entries = [VerbEntry(base="go", past="went", pp="gone", ru="идти")]

    await verb_service.sync_verbs(db, user, entries)
    await verb_service.sync_verbs(db, user, entries)

    pairs = await pairs_repo.list_active(db, user.id, source="VERB")
    assert len(pairs) == 1


@pytest.mark.asyncio
async def test_sync_verb_update_ru_preserves_cards(db):
    from app.repositories import cards as cards_repo

    user = await users_repo.get_or_create(db, 1, "Europe/Moscow")
    await db.commit()

    await verb_service.sync_verbs(db, user, [VerbEntry(base="go", past="went", pp="gone", ru="идти")])
    pairs = await pairs_repo.list_active(db, user.id, source="VERB")
    pair = pairs[0]
    cards_before = await cards_repo.get_for_pair(db, pair.id)
    assert len(cards_before) == 2

    await verb_service.sync_verbs(db, user, [VerbEntry(base="go", past="went", pp="gone", ru="ехать")])
    await db.refresh(pair)
    assert pair.russian == "ехать"

    cards_after = await cards_repo.get_for_pair(db, pair.id)
    assert len(cards_after) == 2
    assert {c.id for c in cards_before} == {c.id for c in cards_after}


@pytest.mark.asyncio
async def test_verb_orphan_flag(db):
    user = await users_repo.get_or_create(db, 1, "Europe/Moscow")
    await db.commit()

    await verb_service.sync_verbs(db, user, [
        VerbEntry(base="go", past="went", pp="gone", ru="идти"),
        VerbEntry(base="do", past="did", pp="done", ru="делать"),
    ])
    await verb_service.sync_verbs(db, user, [
        VerbEntry(base="go", past="went", pp="gone", ru="идти"),
    ])

    pairs = await pairs_repo.list_active(db, user.id, source="VERB")
    by_base = {p.verb_base: p for p in pairs}
    assert by_base["do"].is_orphaned is True
    assert by_base["go"].is_orphaned is False


@pytest.mark.asyncio
async def test_verb_returns_from_orphan(db):
    user = await users_repo.get_or_create(db, 1, "Europe/Moscow")
    await db.commit()

    await verb_service.sync_verbs(db, user, [VerbEntry(base="do", past="did", pp="done", ru="делать")])
    await verb_service.sync_verbs(db, user, [])
    pairs = await pairs_repo.list_active(db, user.id, source="VERB")
    assert pairs[0].is_orphaned is True

    await verb_service.sync_verbs(db, user, [VerbEntry(base="do", past="did", pp="done", ru="делать")])
    pairs = await pairs_repo.list_active(db, user.id, source="VERB")
    assert pairs[0].is_orphaned is False


# --- sessions isolation ---

@pytest.mark.asyncio
async def test_verb_session_isolated_from_user(db):
    user = await users_repo.get_or_create(db, 1, "Europe/Moscow")
    await db.commit()

    await pair_service.create_pair(db, user, "warehouse", "склад")
    await verb_service.sync_verbs(db, user, [
        VerbEntry(base="go", past="went", pp="gone", ru="идти"),
    ])

    user_session = await session_service.build_session(db, user, session_type="USER")
    from app.repositories import sessions as sessions_repo
    sc = await sessions_repo.next_pending(db, user_session.id)
    assert sc.card.pair.source == "USER"

    verb_session = await session_service.build_session(db, user, session_type="VERB")
    sc = await sessions_repo.next_pending(db, verb_session.id)
    assert sc.card.pair.source == "VERB"


@pytest.mark.asyncio
async def test_verb_session_min_size(db):
    user = await users_repo.get_or_create(db, 1, "Europe/Moscow")
    await db.commit()

    await verb_service.sync_verbs(db, user, [
        VerbEntry(base="go", past="went", pp="gone", ru="идти"),
    ])

    session = await session_service.build_session(db, user, session_type="VERB")
    from app.repositories import sessions as sessions_repo
    total = await sessions_repo.count_total(db, session.id)
    # 2 карточки — меньше MIN_SESSION_SIZE, но доступно ровно столько
    assert total == 2


@pytest.mark.asyncio
async def test_orphan_in_archive_not_in_session(db):
    from app.repositories import cards as cards_repo
    from app.domain import srs

    user = await users_repo.get_or_create(db, 1, "Europe/Moscow")
    await db.commit()

    await verb_service.sync_verbs(db, user, [
        VerbEntry(base="go", past="went", pp="gone", ru="идти"),
        VerbEntry(base="do", past="did", pp="done", ru="делать"),
    ])
    pairs = await pairs_repo.list_active(db, user.id, source="VERB")
    by_base = {p.verb_base: p for p in pairs}

    for card in await cards_repo.get_for_pair(db, by_base["do"].id):
        card.state = srs.ARCHIVE
    await db.commit()

    # удалить do из JSON → is_orphaned
    await verb_service.sync_verbs(db, user, [
        VerbEntry(base="go", past="went", pp="gone", ru="идти"),
    ])

    session = await session_service.build_session(db, user, session_type="VERB")
    # в сессии должны быть только карточки go
    from app.repositories import sessions as sessions_repo
    seen = set()
    while True:
        sc = await sessions_repo.next_pending(db, session.id)
        if sc is None:
            break
        seen.add(sc.card.pair.verb_base)
        sc.status = "ANSWERED"
        await db.commit()
    assert "do" not in seen

