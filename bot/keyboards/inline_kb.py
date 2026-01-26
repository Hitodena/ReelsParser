from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_start_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for start message."""
    keyboard = [
        [
            InlineKeyboardButton(
                text="Начать парсинг", callback_data="start_parse"
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Keyboard with cancel button."""
    keyboard = [
        [InlineKeyboardButton(text="Отмена", callback_data="cancel")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
