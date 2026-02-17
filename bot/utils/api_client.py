import httpx
from aiogram.types import BufferedInputFile

from app.core import load

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
        response.raise_for_status()

    return response.json()


async def create_payment(tg_id: int, plan_type: str) -> dict[str, str]:
    """Call API to get payment info"""
    url = f"{config.environment.api_base_url}/payments/create"

    data = {"plan_type": plan_type, "tg_id": tg_id}

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=data, timeout=15)
        response.raise_for_status()

    return response.json()


async def get_limit(tg_id: int) -> dict[str, bool | int]:
    url = f"{config.environment.api_base_url}/users/{tg_id}/limit"

    async with httpx.AsyncClient() as client:
        response = await client.get(url, timeout=15)
        response.raise_for_status()

    return response.json()
