from pydantic import Field
from pydantic_settings import BaseSettings


class BotSettings(BaseSettings):
    """Bot configuration settings"""

    bot_token: str = Field(description="Telegram bot token")
    redis_url: str = Field(
        description="Redis URL for FSM storage",
    )
    api_base_url: str = Field(description="Base URL for the app API")
