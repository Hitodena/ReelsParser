import httpx
from aiogram.types import BufferedInputFile

from app.core import load
from bot.exceptions import (
    AlreadyHasPlanError,
    NoAccountsForParsingError,
    PlanNotFound,
    PrivateAccountError,
    UnexpectedError,
    UserNotFoundError,
)

config = load()


async def parse_instagram_reels(
    username: str, max_reels: int | None
) -> BufferedInputFile:
    """Call API to parse Instagram reels and get XLSX file."""
    url = f"{config.environment.api_base_url}/instagram/parse/xlsx"

    data = {
        "target_username": username,
        "max_reels": max_reels,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=data, timeout=600)

        if response.status_code == 403:
            raise PrivateAccountError(username)
        elif response.status_code == 404:
            raise NoAccountsForParsingError()

        response.raise_for_status()

        # Get file
        content = response.content
        filename = f"{username}_reels.xlsx"

        return BufferedInputFile(content, filename=filename)


async def get_plans() -> list[dict[str, str | int]]:
    """Call API to get tariffs"""
    url = f"{config.environment.api_base_url}/plans"

    async with httpx.AsyncClient() as client:
        response = await client.get(url, timeout=15)

        if response.status_code == 500:
            raise UnexpectedError()

        response.raise_for_status()

    return response.json()["plans"]


async def create_payment(tg_id: int, plan_type: str) -> dict[str, str]:
    """Call API to get payment info"""
    url = f"{config.environment.api_base_url}/payments/create"

    data = {"plan_type": plan_type, "tg_id": tg_id}

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=data, timeout=15)

        if response.status_code == 400:
            # User already has a paid plan
            error_detail = response.json().get(
                "detail", "У вас уже есть активный тариф"
            )
            raise AlreadyHasPlanError(error_detail)

        if response.status_code == 500:
            raise UnexpectedError()

        response.raise_for_status()

    return response.json()


async def get_limit(tg_id: int) -> dict[str, bool | int]:
    """Call API to get user limit"""
    url = f"{config.environment.api_base_url}/users/{tg_id}/limit"

    async with httpx.AsyncClient() as client:
        response = await client.get(url, timeout=15)

        if response.status_code == 404:
            raise UserNotFoundError()

        response.raise_for_status()

    return response.json()


async def increment_usage(tg_id: int) -> dict[str, bool | int]:
    """Call API to increment user requests"""
    url = f"{config.environment.api_base_url}/users/{tg_id}/increment"

    async with httpx.AsyncClient() as client:
        response = await client.post(url, timeout=15)

        if response.status_code == 404:
            raise UserNotFoundError()

        response.raise_for_status()

    return response.json()


async def register_user(tg_id: int):
    """Call API to register user"""
    url = f"{config.environment.api_base_url}/users/{tg_id}/register"

    async with httpx.AsyncClient() as client:
        response = await client.post(url, timeout=15)

        if response.status_code == 404:
            raise PlanNotFound()

        if response.status_code == 500:
            raise UnexpectedError()

        response.raise_for_status()

    return response.json()


async def get_profile(tg_id: int) -> dict[str, str | int | bool | None]:
    """Call API to get user profile"""
    url = f"{config.environment.api_base_url}/users/{tg_id}/profile"

    async with httpx.AsyncClient() as client:
        response = await client.get(url, timeout=15)

        if response.status_code == 404:
            raise UserNotFoundError()

        if response.status_code == 500:
            raise UnexpectedError()

        response.raise_for_status()

    return response.json()
