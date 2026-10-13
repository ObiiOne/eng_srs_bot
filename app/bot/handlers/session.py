from html import escape

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards.main import (
    active_session_kb,
    main_menu_kb,
    session_control_kb,
)
from app.bot.states import SessionFlow
from app.domain import srs
from app.services import session_service

router = Router()


async def _show_next(message: Message, db, user, session) -> None:
    sc = await session_service.sessions_repo.next_pending(db, session.id)
    if sc is None:
        answered, total = await session_service.session_progress(db, session)
        await message.answer(
            f"🎉 Сессия завершена ({answered}/{total}).",
            reply_markup=main_menu_kb(),
        )
        return

    card = sc.card
    shown, _, direction = session_service.question_for(card)
    answered, total = await session_service.session_progress(db, session)

    parts = [f"<b>{answered + 1} / {total}</b>"]
    if session.session_type == "VERB":
        parts.append("ГЛАГОЛЫ")
    parts.append(direction)
    header = "  ·  ".join(parts)

    await message.answer(
        f"{header}\n\n"
        f"<b>{escape(shown)}</b>\n\n"
        f"Ваш ответ:",
        reply_markup=session_control_kb(),
    )


@router.callback_query(F.data == "menu:review")
async def cb_start_review(callback: CallbackQuery, state: FSMContext, db, user):
    active = await session_service.get_any_active_session(db, user)
    if active is not None:
        await callback.message.answer(
            "У вас уже есть активная сессия.",
            reply_markup=active_session_kb(),
        )
        await callback.answer()
        return

    session = await session_service.build_session(db, user, session_type="USER")
    if session is None:
        await callback.message.answer(
            "Нет доступных карточек. Сначала добавьте пару.",
            reply_markup=main_menu_kb(),
        )
        await callback.answer()
        return

    await state.set_state(SessionFlow.active)
    await callback.message.answer("▶️ Начинаем сессию повторения.")
    await _show_next(callback.message, db, user, session)
    await callback.answer()


@router.callback_query(F.data == "verbs:start")
async def cb_start_verbs(callback: CallbackQuery, state: FSMContext, db, user):
    active = await session_service.get_any_active_session(db, user)
    if active is not None:
        await callback.message.answer(
            "У вас уже есть активная сессия.",
            reply_markup=active_session_kb(),
        )
        await callback.answer()
        return

    session = await session_service.build_session(db, user, session_type="VERB")
    if session is None:
        await callback.message.answer(
            "Пока нет глаголов для повторения.",
            reply_markup=main_menu_kb(),
        )
        await callback.answer()
        return

    await state.set_state(SessionFlow.active)
    await callback.message.answer("▶️ Начинаем сессию по глаголам.")
    await _show_next(callback.message, db, user, session)
    await callback.answer()


@router.callback_query(F.data == "session:continue")
async def cb_continue(callback: CallbackQuery, state: FSMContext, db, user):
    session = await session_service.get_any_active_session(db, user)
    if session is None:
        await callback.message.answer("Активной сессии нет.", reply_markup=main_menu_kb())
        await state.clear()
        await callback.answer()
        return
    await state.set_state(SessionFlow.active)
    await _show_next(callback.message, db, user, session)
    await callback.answer()


@router.callback_query(F.data == "session:interrupt")
async def cb_interrupt(callback: CallbackQuery, state: FSMContext, db, user):
    session = await session_service.get_any_active_session(db, user)
    if session is not None:
        await session_service.interrupt_session(db, session)
    await state.clear()
    await callback.message.answer("⏹ Сессия прервана.", reply_markup=main_menu_kb())
    await callback.answer()


@router.message(SessionFlow.active, F.text, ~F.text.startswith("/"))
async def on_answer(message: Message, state: FSMContext, db, user):
    session = await session_service.get_any_active_session(db, user)
    if session is None:
        await state.clear()
        await message.answer(
            "Сессия не найдена. Возможно, она истекла.", reply_markup=main_menu_kb()
        )
        return

    answer = (message.text or "").strip()
    result = await session_service.process_answer(db, user, session, answer)

    if result.get("done"):
        await state.clear()
        await message.answer("Сессия уже завершена.", reply_markup=main_menu_kb())
        return

    if result["is_correct"]:
        await message.answer(
            f"✅ Верно!\n"
            f"Уровень: {srs.label(result['state_before'])} → "
            f"{srs.label(result['state_after'])}"
        )
    else:
        await message.answer(
            f"❌ Неверно.\nПравильный ответ: <b>{escape(result['expected'])}</b>\n"
            f"Уровень: {srs.label(result['state_before'])} → "
            f"{srs.label(result['state_after'])}"
        )

    if result["finished"]:
        await state.clear()
        answered, total = await session_service.session_progress(db, session)
        await message.answer(
            f"🎉 Сессия завершена ({answered}/{total}).",
            reply_markup=main_menu_kb(),
        )
        return

    await _show_next(message, db, user, session)
    