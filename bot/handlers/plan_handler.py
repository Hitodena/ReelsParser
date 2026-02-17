from aiogram import Dispatcher
from aiogram.filters import Command
from aiogram.types import Message

from bot.keyboards import get_plans_keyboard
from bot.utils import get_plans


async def plans_command(message: Message):
    """Handler for /plan command."""
    plans = await get_plans()
    await message.answer(
        "Choose plan:", reply_markup=get_plans_keyboard(plans)
    )


def register(dp: Dispatcher):
    """Register handlers."""
    dp.message.register(plans_command, Command("plans"))
