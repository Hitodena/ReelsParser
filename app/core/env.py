from typing import Sequence

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app import ENV_FILE
from app.custom_enums import AppEnvironment, LogLevel


class EnvironmentSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_environment: AppEnvironment = Field(default=AppEnvironment.DEV)
    log_level: LogLevel = Field(default=LogLevel.DEBUG)
    debug: bool = Field(default=True)

    db_user: str = Field(default="postgres")
    db_password: str = Field(default="postgres")
    db_host: str = Field(default="localhost")
    db_port: int = Field(default=5432)
    db_name: str = Field(default="postgres")

    redis_url: str = Field(default="redis://localhost:6379")

    cors_allow_origins: Sequence[str] = Field(default=["*"])
    cors_allow_credentials: bool = Field(default=True)

    log_console_formatter: str = Field(
        default="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level> |"
        "<yellow>({extra})</yellow>"
    )
    log_file_formatter: str = Field(
        default="{time:YYYY-MM-DD HH:mm:ss} | "
        "{level} | "
        "{name}:{function}:{line} | "
        "{message} | {extra}"
    )

    def get_db_url(self) -> str:
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
