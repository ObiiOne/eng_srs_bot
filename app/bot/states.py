from aiogram.fsm.state import State, StatesGroup


class AddPairFlow(StatesGroup):
    english = State()
    russian = State()
    confirm = State()


class EditPairFlow(StatesGroup):
    menu = State()
    english = State()
    russian = State()


class SessionFlow(StatesGroup):
    active = State()


class EarlyFlow(StatesGroup):
    active = State()
    