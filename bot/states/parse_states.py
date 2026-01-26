from aiogram.fsm.state import State, StatesGroup


class ParseStates(StatesGroup):
    username = State()
    max_reels = State()
