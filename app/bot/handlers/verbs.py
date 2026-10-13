import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.bot.keyboards.main import main_menu_kb, verbs_menu_kb
from app.config import settings
from app.domain.verbs import VerbConfigError, load_verbs
from app.services import verb_service

router = Router()
log = logging.getLogger(__name__)


@router.callback_query(F.data == "menu:verbs")
async def cb_verbs_menu(callback: CallbackQuery, state: FSMContext, db, user):
    await state.clear()

    try:
        entries = load_verbs(settings.verbs_path)
    except VerbConfigError as e:
        log.error("Ошибка в файле глаголов: %s", e)
        await callback.message.answer(
            "⚠️ Список глаголов временно недоступен.",
            reply_markup=main_menu_kb(),
        )
        await callback.answer()
        return

    await verb_service.sync_verbs(db, user, entries)

    await callback.message.answer(
        "📖 <b>Неправильные глаголы</b>\n\nЧто делаем?",
        reply_markup=verbs_menu_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "verbs:stats")
async def cb_verbs_stats(callback: CallbackQuery, db, user):
    s = await verb_service.build_verb_stats(db, user)
    text = (
        "📊 <b>Статистика · Глаголы</b>\n\n"
        f"Глаголов: <b>{s['pairs']}</b>\n"
        f"Активных карточек: <b>{s['active_cards']}</b>\n"
        f"В архиве: <b>{s['archive_cards']}</b>\n"
        f"К повторению сейчас: <b>{s['due_today']}</b>\n\n"
        f"Правильных: <b>{s['correct']}</b>\n"
        f"Ошибок: <b>{s['errors']}</b>\n"
        f"Всего: <b>{s['total']}</b>\n"
        f"Процент: <b>{s['percent']:.1f}%</b>"
    )
    await callback.message.answer(text, reply_markup=verbs_menu_kb())
    await callback.answer()

