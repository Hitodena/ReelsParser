from aiogram import Dispatcher, F
from aiogram.types import CallbackQuery

from bot.utils import create_payment


async def pay_plan(callback: CallbackQuery):
    """Handler for /pay command."""
    plan_id = callback.data.split("_")[1]  # pyright: ignore[reportOptionalMemberAccess]
    payment = await create_payment(callback.from_user.id, plan_id)
    await callback.answer()
    await callback.message.answer(  # pyright: ignore[reportOptionalMemberAccess]
        f"Ссылка для оплаты: {payment['payment_url']}"
    )


def register(dp: Dispatcher):
    """Register handlers."""
    dp.message.register(pay_plan, F.data.startswith("plan_"))
