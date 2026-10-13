from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="📖 Неправильные глаголы", callback_data="menu:verbs")
    kb.button(text="▶️ Начать повторение", callback_data="menu:review")
    kb.button(text="➕ Добавить пару", callback_data="menu:add")
    kb.button(text="📚 Мои пары", callback_data="menu:pairs")
    kb.button(text="🔁 Раннее повторение", callback_data="menu:early")
    kb.button(text="📊 Статистика", callback_data="menu:stats")
    kb.adjust(1)
    return kb.as_markup()


def verbs_menu_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="▶️ Учить глаголы", callback_data="verbs:start")
    kb.button(text="🔁 Раннее повторение глаголов", callback_data="verbs:early")
    kb.button(text="📊 Статистика глаголов", callback_data="verbs:stats")
    kb.button(text="⬅️ В меню", callback_data="menu:main")
    kb.adjust(1)
    return kb.as_markup()


def cancel_kb(callback: str = "flow:cancel") -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="❌ Отмена", callback_data=callback)
    return kb.as_markup()


def confirm_kb(confirm_cb: str, cancel_cb: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Подтвердить", callback_data=confirm_cb)
    kb.button(text="❌ Отмена", callback_data=cancel_cb)
    kb.adjust(1)
    return kb.as_markup()


def session_control_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="⏹ Прервать сессию", callback_data="session:interrupt")
    kb.adjust(1)
    return kb.as_markup()


def active_session_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="▶️ Продолжить сессию", callback_data="session:continue")
    kb.button(text="⏹ Прервать сессию", callback_data="session:interrupt")
    kb.adjust(1)
    return kb.as_markup()


def pair_detail_kb(pair_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✏️ Редактировать", callback_data=f"pair:edit:{pair_id}")
    kb.button(text="🗑 Удалить", callback_data=f"pair:del:{pair_id}")
    kb.button(text="⬅️ К списку", callback_data="menu:pairs")
    kb.adjust(1)
    return kb.as_markup()


def edit_menu_kb(pair_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✏️ Английское", callback_data=f"pair:edit_en:{pair_id}")
    kb.button(text="✏️ Русское", callback_data=f"pair:edit_ru:{pair_id}")
    kb.button(text="✅ Сохранить", callback_data=f"pair:save:{pair_id}")
    kb.button(text="❌ Отмена", callback_data=f"pair:view:{pair_id}")
    kb.adjust(1)
    return kb.as_markup()


def pairs_list_kb(pairs: list) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for p in pairs:
        label = f"{p.english} → {p.russian}"
        if len(label) > 60:
            label = label[:57] + "…"
        kb.button(text=label, callback_data=f"pair:view:{p.id}")
    kb.button(text="⬅️ В меню", callback_data="menu:main")
    kb.adjust(1)
    return kb.as_markup()
