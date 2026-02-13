from aiogram.fsm.state import State, StatesGroup


class UserStates(StatesGroup):
    ASK_NICK = State()
    CHOOSE_FORMAT = State()
    CHOOSE_LIMIT = State()
    CONFIRM = State()

