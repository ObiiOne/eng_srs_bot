from html import escape

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards.main import main_menu_kb
from app.bot.states import EarlyFlow
from app.services import session_service

router = Router()


async def _show_current(message: Message, db, state: FSMContext, user) -> None:
    data = await state.get_data()
    ids: list[int] = data.get("early_ids", [])
    idx: int = data.get("early_idx", 0)
    label: str = data.get("early_label", "")

    if idx >= len(ids):
        await state.clear()
        await message.answer(
            "🔁 Досрочное повторение завершено. SRS не изменялся.",
            reply_markup=main_menu_kb(),
        )
        return

    card = await session_service.cards_repo.get_by_id(db, ids[idx])
    if card is None or card.pair is None or card.pair.deleted_at is not None:
        await state.update_data(early_idx=idx + 1)
        await _show_current(message, db, state, user)
        return

    shown, _, direction = session_service.question_for(card)
    header = f"<b>{idx + 1} / {len(ids)}</b>"
    if label:
        header += f"  ·  {label}"
    header += f"  ·  {direction}"

    await message.answer(
        f"{header}\n\n"
        f"<b>{escape(shown)}</b>\n\nВаш ответ:"
    )


@router.callback_query(F.data == "menu:early")
async def cb_start_early(callback: CallbackQuery, state: FSMContext, db, user):
    cards = await session_service.get_early_review_cards(db, user, source="USER")
    if not cards:
        await callback.message.answer(
            "Сегодня ещё не было обычных повторений — нечего тренировать.",
            reply_markup=main_menu_kb(),
        )
        await callback.answer()
        return

    await state.set_state(EarlyFlow.active)
    await state.update_data(early_ids=[c.id for c in cards], early_idx=0, early_label="")
    await callback.message.answer(
        f"🔁 Досрочное повторение: {len(cards)} карточек.\nSRS не будет изменяться."
    )
    await _show_current(callback.message, db, state, user)
    await callback.answer()


@router.callback_query(F.data == "verbs:early")
async def cb_start_verb_early(callback: CallbackQuery, state: FSMContext, db, user):
    cards = await session_service.get_early_review_cards(db, user, source="VERB")
    if not cards:
        await callback.message.answer(
            "Сегодня ещё не было повторений глаголов — нечего тренировать.",
            reply_markup=main_menu_kb(),
        )
        await callback.answer()
        return

    await state.set_state(EarlyFlow.active)
    await state.update_data(
        early_ids=[c.id for c in cards], early_idx=0, early_label="ГЛАГОЛЫ"
    )
    await callback.message.answer(
        f"🔁 Раннее повторение глаголов: {len(cards)} карточек.\nSRS не будет изменяться."
    )
    await _show_current(callback.message, db, state, user)
    await callback.answer()


@router.message(EarlyFlow.active, F.text, ~F.text.startswith("/"))
async def on_early_answer(message: Message, state: FSMContext, db, user):
    data = await state.get_data()
    ids: list[int] = data.get("early_ids", [])
    idx: int = data.get("early_idx", 0)
    if idx >= len(ids):
        await state.clear()
        await message.answer("Готово.", reply_markup=main_menu_kb())
        return

    card = await session_service.cards_repo.get_by_id(db, ids[idx])
    if card is None:
        await state.update_data(early_idx=idx + 1)
        await _show_current(message, db, state, user)
        return

    result = await session_service.process_early_answer(
        db, user, card, (message.text or "").strip()
    )
    if result["is_correct"]:
        await message.answer("✅ Верно (тренировка, SRS не изменён).")
    else:
        await message.answer(
            f"❌ Неверно. Правильный ответ: <b>{escape(result['expected'])}</b>\n"
            f"(тренировка, SRS не изменён)"
        )

    await state.update_data(early_idx=idx + 1)
    await _show_current(message, db, state, user)
    