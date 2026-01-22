import sys
from pathlib import Path

from loguru import logger

from ..custom_enums import LogLevel
from .env import EnvironmentSettings
from .settings import Logs


class LoggerSettings:
    def __init__(
        self,
        log_settings: Logs,
        settings: EnvironmentSettings,
        modules: list[str] | None = None,
    ):
        self.log_settings = log_settings
        self.settings = settings
        self.modules = modules
        self.setup_logger()

    def setup_logger(self) -> None:
        log_level = self.settings.log_level
        file_level = self.log_settings.file_log_level
        console_format = self.settings.log_console_formatter
        file_format = self.settings.log_file_formatter
        rotation = "10 MB"
        retention = "7 days"
        compression = "zip"
        serialize = False
        backtrace = True
        diagnose = False
        enqueue = True
        log_dir: Path = Path("logs")
        if not log_dir.exists():
            log_dir.mkdir(parents=True, exist_ok=True)

        logger.remove()
        logger.add(
            sys.stderr,
            level=log_level,
            format=console_format,
            colorize=True,
            backtrace=backtrace,
            diagnose=diagnose,
            enqueue=enqueue,
        )
        logger.add(
            log_dir / "errors.log",
            level=LogLevel.ERROR,
            format=file_format,
            rotation=rotation,
            retention=retention,
            compression=compression,
            serialize=serialize,
            backtrace=backtrace,
            diagnose=diagnose,
            enqueue=enqueue,
        )
        logger.add(
            log_dir / "app.log",
            level=log_level,
            format=file_format,
            rotation=rotation,
            retention=retention,
            compression=compression,
            serialize=serialize,
            backtrace=backtrace,
            diagnose=diagnose,
            enqueue=enqueue,
        )

        if self.modules:
            for module_name in self.modules:
                logger.add(
                    log_dir / f"{module_name.replace('.', '_')}.log",
                    level=file_level,
                    format=file_format,
                    filter=module_name,
                    rotation=rotation,
                    retention=retention,
                    compression=compression,
                    serialize=serialize,
                    backtrace=backtrace,
                    diagnose=diagnose,
                    enqueue=enqueue,
                )
