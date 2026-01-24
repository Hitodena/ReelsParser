from functools import lru_cache

from pydantic import Field
from pydantic_settings import (
    BaseSettings,
)

from .env import EnvironmentSettings
from .logging_settings import LoggerSettings
from .settings import Identifiers, Logs, Network, Parsing, Retries, Timeouts


class Config(BaseSettings):
    environment: EnvironmentSettings = Field(
        default_factory=EnvironmentSettings
    )
    logs: Logs = Field(default_factory=Logs)
    timeouts: Timeouts = Field(default_factory=Timeouts)
    network: Network = Field(default_factory=Network)
    retries: Retries = Field(default_factory=Retries)
    parsing: Parsing = Field(default_factory=Parsing)
    identifiers: Identifiers = Field(default_factory=Identifiers)


config = Config()


@lru_cache
def load() -> Config:
    """Load configuration with all values

    Returns:
        Config: Config Object
    """
    env = config.environment
    logs = config.logs
    _ = LoggerSettings(logs, env)
    return config
