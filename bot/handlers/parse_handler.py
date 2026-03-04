import re

from aiogram import Dispatcher, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.exceptions import (
    NoAccountsForParsingError,
    PrivateAccountError,
    UnexpectedError,
    UserNotFoundError,
)
from bot.keyboards import get_cancel_keyboard
from bot.states import ParseStates
from bot.utils import get_limit, increment_usage, parse_instagram_reels


async def parse_command(message: Message, state: FSMContext):
    """Handler for /parse command."""
    await state.set_state(ParseStates.username)
    await message.answer(
        "Введите username Instagram аккаунта (например, iamrigbycat):",
        reply_markup=get_cancel_keyboard(),
    )


async def username_input(message: Message, state: FSMContext):
    """Handle username input."""
    username = message.text.strip()  # pyright: ignore[reportOptionalMemberAccess]

    # Check user limit
    try:
        limit = await get_limit(message.from_user.id)  # pyright: ignore[reportOptionalMemberAccess]
    except UserNotFoundError as exc:
        await message.answer(exc.message)
        await state.clear()
        return

    if not limit["can_parse"]:
        await message.answer(
            f"Вы исчерпали лимит парсинга. Осталось: {limit['remaining']}"
        )
        await state.clear()
        return

    # Validate username
    if not re.match(r"^[a-zA-Z0-9_.]+$", username):
        await message.answer(
            "Некорректный username. Используйте только буквы, цифры, точки и подчеркивания.",
            reply_markup=get_cancel_keyboard(),
        )
        return

    await state.update_data(username=username)
    await message.answer("Начинаю парсинг... Пожалуйста, подождите.")

    try:
        file_content = await parse_instagram_reels(
            username, limit["max_reels"]
        )

        # Send file
        await message.answer_document(
            document=file_content,
            filename=f"{username}_reels.xlsx",
            caption="Парсинг завершен! Вот ваш файл с reels.",
        )

        # Increment usage only on success
        await increment_usage(message.from_user.id)  # pyright: ignore[reportOptionalMemberAccess]

        # Ask for username again (stay in the same state)
        await message.answer(
            "Введите username следующего Instagram аккаунта:",
            reply_markup=get_cancel_keyboard(),
        )
        return

    except PrivateAccountError as exc:
        await message.answer(exc.message)
    except NoAccountsForParsingError as exc:
        await message.answer(exc.message)
    except UnexpectedError as exc:
        await message.answer(exc.message)
    except Exception:
        await message.answer(
            "Произошла ошибка при парсинге. Попробуйте /parse снова."
        )

    await state.clear()


async def start_parse_callback(callback: CallbackQuery, state: FSMContext):
    """Handle callback for starting parsing."""
    await callback.answer()
    await parse_command(callback.message, state)  # type: ignore


async def cancel_callback(callback: CallbackQuery, state: FSMContext):
    """Handle callback for canceling."""
    await callback.answer()
    await state.clear()
    await callback.message.answer("Операция отменена.")  # type: ignore


async def cancel_text(message: Message, state: FSMContext):
    """Handle text 'cancel' to cancel operation immediately."""
    current_state = await state.get_state()
    if current_state is not None:
        await state.clear()
        await message.answer("Операция отменена.")


def register(dp: Dispatcher):
    """Register handlers."""
    dp.message.register(parse_command, Command("parse"))
    dp.message.register(username_input, ParseStates.username)
    dp.message.register(cancel_text, F.text.lower() == "cancel")
    dp.callback_query.register(start_parse_callback, F.data == "start_parse")
    dp.callback_query.register(cancel_callback, F.data == "cancel")
