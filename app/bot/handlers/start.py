from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards.main import active_session_kb, main_menu_kb
from app.services import session_service

router = Router()

WELCOME = (
    "👋 <b>Telegram SRS English Bot</b>\n\n"
    "Я помогу запоминать английские слова и выражения методом интервального повторения.\n\n"
    "Ты сам создаёшь пары «английское выражение → свой перевод», "
    "а я напоминаю, что и когда повторить, и строго проверяю ответ."
)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, db, user):
    active = await session_service.get_any_active_session(db, user)
    if active is not None:
        answered, total = await session_service.session_progress(db, active)
        await message.answer(
            f"⏸ У вас есть незавершённая сессия ({answered}/{total}).\n"
            "Продолжить или прервать?",
            reply_markup=active_session_kb(),
        )
        return

    await state.clear()
    await message.answer(WELCOME, reply_markup=main_menu_kb())


@router.callback_query(F.data == "menu:main")
async def cb_main_menu(callback: CallbackQuery, state: FSMContext, db, user):
    await state.clear()
    active = await session_service.get_any_active_session(db, user)
    if active is not None:
        await callback.message.answer(
            "У вас есть активная сессия. Продолжить или прервать?",
            reply_markup=active_session_kb(),
        )
        await callback.answer()
        return
    await callback.message.answer("Главное меню:", reply_markup=main_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "flow:cancel")
async def cb_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("Отменено.", reply_markup=main_menu_kb())
    await callback.answer()
    