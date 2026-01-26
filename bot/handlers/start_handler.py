from aiogram import Dispatcher
from aiogram.filters import Command
from aiogram.types import Message

from bot.keyboards import get_start_keyboard


async def start_command(message: Message):
    """Handler for /start command."""
    text = "Используйте /parse для начала процесса парсинга reels."
    await message.answer(text, reply_markup=get_start_keyboard())


def register(dp: Dispatcher):
    """Register the handler."""
    dp.message.register(start_command, Command("start"))
