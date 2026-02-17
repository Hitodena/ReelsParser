from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject, Update

from bot.exceptions import UserNotFoundError
from bot.utils import get_limit


class AuthMiddleware(BaseMiddleware):
    """Check if user exists in DB before working"""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        # Get message from Update if applicable
        message = None
        if isinstance(event, Update) and event.message:
            message = event.message
        elif isinstance(event, Message):
            message = event

        # Skip /start command
        if message and message.text and message.text.startswith("/start"):
            return await handler(event, data)

        user = data.get("event_from_user")
        if not user:
            return await handler(event, data)

        # Check registration via API
        try:
            limit = await get_limit(user.id)
            data["user_limit"] = limit
            return await handler(event, data)
        except UserNotFoundError:
            if message:
                await message.answer("Сначала введите /start для регистрации")
            return  # Don't call handler
        except Exception:
            if message:
                await message.answer(
                    "Ошибка проверки регистрации. Попробуйте позже."
                )
            return
