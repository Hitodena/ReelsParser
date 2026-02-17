from aiogram import Dispatcher
from aiogram.filters import Command
from aiogram.types import Message

from bot.exceptions import PlanNotFound, UnexpectedError
from bot.keyboards import get_start_keyboard
from bot.utils import register_user


async def start_command(message: Message):
    """Handler for /start command."""
    try:
        result = await register_user(message.from_user.id)  # pyright: ignore[reportOptionalMemberAccess]

        if result.get("status") == "created":
            await message.answer(
                "Добро пожаловать! Вы зарегистрированы.",
                reply_markup=get_start_keyboard(),
            )
        else:
            await message.answer(
                "Вы уже зарегистрированы.",
                reply_markup=get_start_keyboard(),
            )
    except PlanNotFound as exc:
        await message.answer(exc.message)
    except UnexpectedError as exc:
        await message.answer(exc.message)
    except Exception:
        await message.answer(
            "Ошибка при регистрации. Попробуйте позже.",
            reply_markup=get_start_keyboard(),
        )


def register(dp: Dispatcher):
    """Register the handler."""
    dp.message.register(start_command, Command("start"))
