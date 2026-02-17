from datetime import datetime

from aiogram import Dispatcher
from aiogram.filters import Command
from aiogram.types import Message

from bot.exceptions import UnexpectedError, UserNotFoundError
from bot.utils import get_profile


async def profile_command(message: Message):
    """Handler for /profile command."""
    try:
        profile = await get_profile(message.from_user.id)  # pyright: ignore[reportOptionalMemberAccess]

        # Format period dates (API returns ISO strings)
        period_start_raw = profile.get("period_start")
        period_end_raw = profile.get("period_end")

        if period_start_raw and isinstance(period_start_raw, str):
            period_start = datetime.fromisoformat(
                period_start_raw.replace("Z", "+00:00")
            ).strftime("%d.%m.%Y")
        else:
            period_start = "N/A"

        if period_end_raw and isinstance(period_end_raw, str):
            period_end = datetime.fromisoformat(
                period_end_raw.replace("Z", "+00:00")
            ).strftime("%d.%m.%Y")
        else:
            period_end = "N/A"

        # Format remaining
        remaining = profile["remaining"]
        if remaining == -1:
            remaining_text = "Безлимит"
        else:
            remaining_text = str(remaining)

        # Format monthly analyses
        monthly = profile["monthly_analyses"]
        if monthly is None:
            monthly_text = "Безлимит"
        else:
            monthly_text = str(monthly)

        text = (
            f"📊 <b>Ваш профиль</b>\n\n"
            f"🔹 <b>Тариф:</b> {profile['plan_name']}\n"
            f"🔹 <b>Использовано:</b> {profile['analyses_used']} / {monthly_text}\n"
            f"🔹 <b>Осталось:</b> {remaining_text}\n"
            f"🔹 <b>Макс. reels за запрос:</b> {profile['max_reels_per_request']}\n"
            f"🔹 <b>Период:</b> {period_start} - {period_end}\n"
        )

        if profile["has_paid_plan"]:
            text += "\n✅ Платный тариф активен"
        else:
            text += "\n💡 Обновите тариф командой /plans"

        await message.answer(text, parse_mode="HTML")

    except UserNotFoundError as exc:
        await message.answer(exc.message)
    except UnexpectedError as exc:
        await message.answer(exc.message)
    except Exception:
        await message.answer("Ошибка при получении профиля. Попробуйте позже.")


def register(dp: Dispatcher):
    """Register handlers."""
    dp.message.register(profile_command, Command("profile"))
