from html import escape

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards.main import (
    cancel_kb,
    confirm_kb,
    edit_menu_kb,
    main_menu_kb,
    pair_detail_kb,
    pairs_list_kb,
)
from app.bot.states import AddPairFlow, EditPairFlow
from app.config import settings
from app.services import pair_service
from app.services.pair_service import PairDuplicateError, PairValidationError

router = Router()


# ---------- ADD ----------

@router.callback_query(F.data == "menu:add")
async def cb_add_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AddPairFlow.english)
    await callback.message.answer(
        "Введите <b>английское</b> слово или выражение:",
        reply_markup=cancel_kb(),
    )
    await callback.answer()


@router.message(AddPairFlow.english, F.text, ~F.text.startswith("/"))
async def add_english(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text or len(text) > settings.max_text_length:
        await message.answer(
            f"Введите непустое значение (до {settings.max_text_length} символов).",
            reply_markup=cancel_kb(),
        )
        return
    await state.update_data(english=text)
    await state.set_state(AddPairFlow.russian)
    await message.answer(
        "Введите <b>русский</b> перевод:",
        reply_markup=cancel_kb(),
    )


@router.message(AddPairFlow.russian, F.text, ~F.text.startswith("/"))
async def add_russian(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text or len(text) > settings.max_text_length:
        await message.answer(
            f"Введите непустое значение (до {settings.max_text_length} символов).",
            reply_markup=cancel_kb(),
        )
        return
    data = await state.get_data()
    en = data.get("english", "")
    await state.update_data(russian=text)
    await state.set_state(AddPairFlow.confirm)
    await message.answer(
        f"Проверьте пару:\n\n"
        f"🇬🇧 <b>{escape(en)}</b>\n"
        f"🇷🇺 <b>{escape(text)}</b>\n\n"
        f"Сохранить?",
        reply_markup=confirm_kb("add:confirm", "flow:cancel"),
    )


@router.callback_query(AddPairFlow.confirm, F.data == "add:confirm")
async def add_confirm(callback: CallbackQuery, state: FSMContext, db, user):
    data = await state.get_data()
    en = data.get("english", "")
    ru = data.get("russian", "")
    try:
        pair = await pair_service.create_pair(db, user, en, ru)
    except PairValidationError as e:
        await callback.message.answer(f"⚠️ {e}", reply_markup=main_menu_kb())
        await state.clear()
        await callback.answer()
        return
    except PairDuplicateError:
        await callback.message.answer(
            "⚠️ Такая пара уже существует.", reply_markup=main_menu_kb()
        )
        await state.clear()
        await callback.answer()
        return

    await state.clear()
    await callback.message.answer(
        f"✅ Пара сохранена.\nСоздано две карточки: EN → RU и RU → EN.",
        reply_markup=main_menu_kb(),
    )
    await callback.answer()


# ---------- LIST ----------

@router.callback_query(F.data == "menu:pairs")
async def cb_list_pairs(callback: CallbackQuery, state: FSMContext, db, user):
    await state.clear()
    pairs = await pair_service.list_pairs(db, user)
    if not pairs:
        await callback.message.answer(
            "У вас пока нет пар. Добавьте первую через «➕ Добавить пару».",
            reply_markup=main_menu_kb(),
        )
        await callback.answer()
        return
    await callback.message.answer(
        f"📚 Ваши пары ({len(pairs)}):",
        reply_markup=pairs_list_kb(pairs),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("pair:view:"))
async def cb_view_pair(callback: CallbackQuery, state: FSMContext, db, user):
    pair_id = int(callback.data.split(":")[2])
    pair = await pair_service.get_pair(db, user, pair_id)
    if pair is None:
        await callback.answer("Пара не найдена.", show_alert=True)
        return
    await state.clear()
    await callback.message.answer(
        f"🇬🇧 <b>{escape(pair.english)}</b>\n"
        f"🇷🇺 <b>{escape(pair.russian)}</b>",
        reply_markup=pair_detail_kb(pair.id),
    )
    await callback.answer()


# ---------- EDIT ----------

@router.callback_query(F.data.startswith("pair:edit:"))
async def cb_edit_pair(callback: CallbackQuery, state: FSMContext, db, user):
    pair_id = int(callback.data.split(":")[2])
    pair = await pair_service.get_pair(db, user, pair_id)
    if pair is None:
        await callback.answer("Пара не найдена.", show_alert=True)
        return
    await state.set_state(EditPairFlow.menu)
    await state.update_data(
        pair_id=pair.id,
        new_english=pair.english,
        new_russian=pair.russian,
    )
    await callback.message.answer(
        f"Редактирование пары:\n\n"
        f"🇬🇧 <b>{escape(pair.english)}</b>\n"
        f"🇷🇺 <b>{escape(pair.russian)}</b>\n\n"
        f"⚠️ После сохранения обе карточки сбросятся в NEW.",
        reply_markup=edit_menu_kb(pair.id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("pair:edit_en:"))
async def cb_edit_en(callback: CallbackQuery, state: FSMContext):
    await state.set_state(EditPairFlow.english)
    await callback.message.answer(
        "Введите новое <b>английское</b> значение:",
        reply_markup=cancel_kb("flow:cancel"),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("pair:edit_ru:"))
async def cb_edit_ru(callback: CallbackQuery, state: FSMContext):
    await state.set_state(EditPairFlow.russian)
    await callback.message.answer(
        "Введите новое <b>русское</b> значение:",
        reply_markup=cancel_kb("flow:cancel"),
    )
    await callback.answer()


@router.message(EditPairFlow.english, F.text, ~F.text.startswith("/"))
async def edit_en_input(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text or len(text) > settings.max_text_length:
        await message.answer("Введите непустое значение.")
        return
    data = await state.get_data()
    await state.update_data(new_english=text)
    await state.set_state(EditPairFlow.menu)
    await message.answer(
        f"Новое английское: <b>{escape(text)}</b>\n"
        f"Текущее русское: <b>{escape(data.get('new_russian', ''))}</b>",
        reply_markup=edit_menu_kb(data["pair_id"]),
    )


@router.message(EditPairFlow.russian, F.text, ~F.text.startswith("/"))
async def edit_ru_input(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text or len(text) > settings.max_text_length:
        await message.answer("Введите непустое значение.")
        return
    data = await state.get_data()
    await state.update_data(new_russian=text)
    await state.set_state(EditPairFlow.menu)
    await message.answer(
        f"Текущее английское: <b>{escape(data.get('new_english', ''))}</b>\n"
        f"Новое русское: <b>{escape(text)}</b>",
        reply_markup=edit_menu_kb(data["pair_id"]),
    )


@router.callback_query(EditPairFlow.menu, F.data.startswith("pair:save:"))
async def cb_edit_save(callback: CallbackQuery, state: FSMContext, db, user):
    data = await state.get_data()
    pair_id = data.get("pair_id")
    en = data.get("new_english", "")
    ru = data.get("new_russian", "")
    if pair_id is None:
        await callback.answer("Сессия редактирования истекла.", show_alert=True)
        await state.clear()
        return
    try:
        await pair_service.update_pair(db, user, pair_id, en, ru)
    except PairValidationError as e:
        await callback.answer(str(e), show_alert=True)
        return
    except PairDuplicateError:
        await callback.answer("Такая пара уже существует.", show_alert=True)
        return
    await state.clear()
    await callback.message.answer(
        "✅ Пара обновлена. Обе карточки сброшены в NEW.",
        reply_markup=main_menu_kb(),
    )
    await callback.answer()


# ---------- DELETE ----------

@router.callback_query(F.data.startswith("pair:del:"))
async def cb_del_pair(callback: CallbackQuery, db, user):
    pair_id = int(callback.data.split(":")[2])
    pair = await pair_service.get_pair(db, user, pair_id)
    if pair is None:
        await callback.answer("Пара не найдена.", show_alert=True)
        return
    await callback.message.answer(
        f"Удалить пару?\n\n"
        f"🇬🇧 <b>{escape(pair.english)}</b>\n"
        f"🇷🇺 <b>{escape(pair.russian)}</b>\n\n"
        f"История ответов сохранится, но пара больше не будет участвовать в обучении.",
        reply_markup=confirm_kb(f"pair:del_confirm:{pair.id}", f"pair:view:{pair.id}"),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("pair:del_confirm:"))
async def cb_del_confirm(callback: CallbackQuery, db, user):
    pair_id = int(callback.data.split(":")[2])
    ok = await pair_service.delete_pair(db, user, pair_id)
    if ok:
        await callback.message.answer("🗑 Пара удалена.", reply_markup=main_menu_kb())
    else:
        await callback.message.answer("Пара не найдена.", reply_markup=main_menu_kb())
    await callback.answer()
