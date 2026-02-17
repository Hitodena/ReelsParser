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


def get_plans_keyboard(
    plans: list[dict[str, str | int]],
) -> InlineKeyboardMarkup:
    """Keyboard with tarrifs"""

    keyboard = [
        [
            InlineKeyboardButton(
                text=f"{plan['name']} - {plan['price_rub']}RUB",
                callback_data=f"plan_{plan['id']}",
            )
        ]
        for plan in plans
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
