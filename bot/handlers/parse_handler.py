import re

import httpx
from aiogram import Dispatcher, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.keyboards import get_cancel_keyboard
from bot.states import ParseStates
from bot.utils import parse_instagram_reels


async def parse_command(message: Message, state: FSMContext):
    """Handler for /parse command."""
    await state.set_state(ParseStates.username)
    await message.answer(
        "Введите username Instagram аккаунта (например, iamrigbycat):",
        reply_markup=get_cancel_keyboard(),
    )


async def username_input(message: Message, state: FSMContext):
    """Handle username input."""
    username = message.text.strip()  # type: ignore

    # Validate username
    if not re.match(r"^[a-zA-Z0-9_.]+$", username):
        await message.answer(
            "Некорректный username. Используйте только буквы, цифры, точки и подчеркивания.",
            reply_markup=get_cancel_keyboard(),
        )
        return

    await state.update_data(username=username)
    await state.set_state(ParseStates.max_reels)
    await message.answer(
        "Введите максимальное количество reels для парсинга (число от 1 до 1000, или 0 для всех):",
        reply_markup=get_cancel_keyboard(),
    )


async def max_reels_input(message: Message, state: FSMContext):
    """Handle max_reels input."""
    text = message.text.strip()  # type: ignore

    if text.lower() == "0":
        max_reels = None
    else:
        try:
            max_reels = int(text)
            if max_reels < 1 or max_reels > 1000:
                raise ValueError
        except ValueError:
            await message.answer(
                "Некорректное значение. Введите число от 1 до 1000, или 0 для всех.",
                reply_markup=get_cancel_keyboard(),
            )
            return

    data = await state.get_data()
    username = data["username"]

    await message.answer("Начинаю парсинг... Пожалуйста, подождите.")

    try:
        file_content = await parse_instagram_reels(username, max_reels)

        # Send file
        await message.answer_document(
            document=file_content,
            filename=f"{username}_reels.xlsx",
            caption="Парсинг завершен! Вот ваш файл с reels.",
        )

    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 403:
            await message.answer(
                "Данный аккаунт приватный\nПопробуйте еще раз с командой /parse."
            )
        elif exc.response.status_code == 404:
            if "No valid Instagram accounts available" in str(
                exc.response.text
            ):
                await message.answer(
                    "Нет аккаунтов для парсинга. Попросите админа добавить аккаунт."
                )
            else:
                await message.answer(
                    "Данный юзернейм не найден\nПопробуйте еще раз с командой /parse."
                )
        else:
            await message.answer(
                "Произошла ошибка при парсинге. \nПопробуйте еще раз с командой /parse."
            )
    except Exception:
        await message.answer(
            "Произошла ошибка при парсинге. \nПопробуйте еще раз с командой /parse."
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
    dp.message.register(max_reels_input, ParseStates.max_reels)
    dp.message.register(cancel_text, F.text.lower() == "cancel")
    dp.callback_query.register(start_parse_callback, F.data == "start_parse")
    dp.callback_query.register(cancel_callback, F.data == "cancel")
