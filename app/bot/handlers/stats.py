from aiogram import F, Router
from aiogram.types import CallbackQuery

from app.bot.keyboards.main import main_menu_kb
from app.services import statistics_service

router = Router()


@router.callback_query(F.data == "menu:stats")
async def cb_stats(callback: CallbackQuery, db, user):
    s = await statistics_service.build_stats(db, user)
    text = (
        "📊 <b>Статистика</b>\n\n"
        f"Пар: <b>{s['pairs']}</b>\n"
        f"Активных карточек: <b>{s['active_cards']}</b>\n"
        f"В архиве: <b>{s['archive_cards']}</b>\n"
        f"К повторению сейчас: <b>{s['due_today']}</b>\n\n"
        f"Правильных ответов: <b>{s['correct']}</b>\n"
        f"Ошибок: <b>{s['errors']}</b>\n"
        f"Всего ответов: <b>{s['total']}</b>\n"
        f"Процент правильных: <b>{s['percent']:.1f}%</b>"
    )
    await callback.message.answer(text, reply_markup=main_menu_kb())
    await callback.answer()
