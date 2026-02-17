from aiogram import Dispatcher, F
from aiogram.types import CallbackQuery

from bot.exceptions import (
    AlreadyHasPlanError,
    UnexpectedError,
    UserNotFoundError,
)
from bot.utils import create_payment


async def pay_plan(callback: CallbackQuery):
    """Handler for payment plan selection."""
    plan_type = callback.data.split("_")[1]  # pyright: ignore[reportOptionalMemberAccess]

    try:
        payment = await create_payment(callback.from_user.id, plan_type)
        await callback.answer()
        await callback.message.answer(  # pyright: ignore[reportOptionalMemberAccess]
            f"Ссылка для оплаты: {payment['payment_url']}"
        )
    except AlreadyHasPlanError as exc:
        await callback.answer()
        await callback.message.answer(exc.message)  # pyright: ignore[reportOptionalMemberAccess]
    except UserNotFoundError as exc:
        await callback.answer()
        await callback.message.answer(exc.message)  # pyright: ignore[reportOptionalMemberAccess]
    except UnexpectedError as exc:
        await callback.answer()
        await callback.message.answer(exc.message)  # pyright: ignore[reportOptionalMemberAccess]
    except Exception:
        await callback.answer()
        await callback.message.answer(  # pyright: ignore[reportOptionalMemberAccess]
            "Ошибка при создании платежа. Попробуйте позже."
        )


def register(dp: Dispatcher):
    """Register handlers."""
    dp.callback_query.register(pay_plan, F.data.startswith("plan_"))
