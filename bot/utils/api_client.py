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
        response = await client.post(url, json=data, timeout=120)

        if response.status_code != 200:
            raise Exception(
                f"API error: {response.status_code} - {response.text}"
            )

        # Get file
        content = response.content
        filename = f"{username}_reels.xlsx"

        return BufferedInputFile(content, filename=filename)
