from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fake_useragent import UserAgent
from loguru import logger
from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    async_playwright,
)

from app.core import Config


class BrowserManager:
    """Browser manager for Playwright."""

    def __init__(self, config: Config) -> None:
        """Initialize the BrowserManager with the given configuration."""
        self._ua = UserAgent(
            browsers=["Chrome", "Google"],
            os=["Windows"],
            platforms=["desktop"],
        )
        self.headless = not config.environment.debug

        self._playwright: Playwright | None = None
        self._browser: Browser | None = None

    async def start(self) -> None:
        """Creates a Playwright browser instance."""
        if self._browser:
            logger.warning("Browser is already started")
            return

        logger.info("Starting Playwright browser...")

        self._playwright = await async_playwright().start()

        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--enable-webgl",
            "--use-gl=swiftshader",
            "--enable-accelerated-2d-canvas",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
        ]

        self._browser = await self._playwright.chromium.launch(
            headless=self.headless, args=launch_args
        )

        logger.info("Playwright browser started")

    async def close(self) -> None:
        """Closes the Playwright browser instance."""
        if not self._browser or not self._playwright:
            logger.warning("Browser is not started")
            return

        logger.info("Closing Playwright browser...")

        await self._browser.close()
        await self._playwright.stop()

        self._browser = None
        self._playwright = None

        logger.info("Playwright browser closed")

    @asynccontextmanager
    async def context(
        self, proxy: dict | None = None
    ) -> AsyncGenerator[tuple[Page, BrowserContext], None]:
        """Create a new browser context and page, optionally with proxy."""
        if not self._browser:
            logger.error("Browser is not started")
            raise RuntimeError(
                "Browser is not started, use start() method first"
            )

        context_options = {
            "locale": "en-US",
            "timezone_id": "Europe/Moscow",
            "viewport": {"width": 1920, "height": 1080},
            "extra_http_headers": {
                "User-Agent": self._ua.random,
                "Accept-Language": "en-US;q=0.9,en-US;q=0.8,en;q=0.7",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Connection": "keep-alive",
            },
        }

        if proxy:
            context_options["proxy"] = proxy

        context = await self._browser.new_context(**context_options)

        await context.add_init_script(
            """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });

            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });

            Object.defineProperty(navigator, 'languages', {
                get: () => ['ru-RU', 'ru', 'en-US', 'en']
            });

            window.chrome = {
                runtime: {}
            };
        """
        )

        page = await context.new_page()

        try:
            logger.bind(proxy=proxy).info("Context and page created")
            yield (page, context)
        finally:
            await page.close()
            await context.close()
            logger.bind(proxy=proxy).info("Context and page closed")
