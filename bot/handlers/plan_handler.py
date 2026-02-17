from aiogram import Dispatcher
from aiogram.filters import Command
from aiogram.types import Message

from bot.exceptions import UnexpectedError
from bot.keyboards import get_plans_keyboard
from bot.utils import get_plans


async def plans_command(message: Message):
    """Handler for /plan command."""
    try:
        plans = await get_plans()
        await message.answer(
            "Выберите тариф:", reply_markup=get_plans_keyboard(plans)
        )
    except UnexpectedError as exc:
        await message.answer(exc.message)
    except Exception:
        await message.answer("Ошибка при получении тарифов. Попробуйте позже.")


def register(dp: Dispatcher):
    """Register handlers."""
    dp.message.register(plans_command, Command("plans"))
