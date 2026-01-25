from loguru import logger
from playwright.async_api import BrowserContext, Page

from app.core import Config
from app.exceptions import AuthCredentialsError, AuthUnexpectedError
from app.models import InstagramAuth
from app.parser import (
    extract_credentials,
    fetch_all_instagram_reels,
    login_to_instagram,
)
from app.services.proxy_manager import ProxyManager


class InstagramOrchestrator:
    """
    Main orchestration service for Instagram operations.

    Handles the full workflow:
    1. Login (if needed)
    2. Extract credentials
    3. Parse reels
    """

    def __init__(self, config: Config, proxy_manager: ProxyManager):
        self.config = config
        self.proxy_manager = proxy_manager

    async def login_and_extract_credentials(
        self, page: Page, ctx: BrowserContext, auth: InstagramAuth
    ) -> dict:
        """
        Login to Instagram and extract GraphQL credentials.

        Args:
            page: Playwright page instance
            ctx: Browser context
            auth: Authentication credentials (login + password OR cookies)

        Returns:
            dict: Credentials containing doc_id, variables, headers, cookies

        Raises:
            AuthCredentialsError: If login fails due to invalid credentials
            AuthUnexpectedError: For unexpected errors
        """
        try:
            logger.bind(login=auth.login).info(
                "Starting login and credential extraction"
            )

            # Step 1: Login
            if not auth.cookies:
                logger.bind(login=auth.login).info("No cookies, logging in")
                cookies = await login_to_instagram(
                    page, ctx, auth, self.config
                )
                auth.cookies = cookies
            else:
                logger.bind(login=auth.login).info("Using existing cookies")

            # Step 2:
            credentials = await extract_credentials(
                page, ctx, auth, self.config
            )

            logger.bind(
                login=auth.login,
                has_doc_id=bool(credentials.get("doc_id")),
                has_cookies=bool(credentials.get("cookies")),
            ).info("Successfully extracted credentials")

            return credentials

        except AuthCredentialsError as exc:
            logger.bind(error_message=exc, login=auth.login).error(
                "Invalid credentials"
            )
            raise
        except AuthUnexpectedError as exc:
            logger.bind(error_message=exc, login=auth.login).error(
                "Unexpected error during extraction"
            )
            raise
        except Exception as exc:
            logger.bind(error_message=exc, login=auth.login).exception(
                "Failed to extract credentials"
            )
            raise AuthUnexpectedError(
                f"Credential extraction failed for {auth.login}: {exc}"
            )

    async def parse_profile_reels(
        self,
        credentials: dict,
        target_username: str,
        max_reels: int | None = None,
    ) -> list[dict]:
        """
        Parse all reels from a target profile using stored credentials.

        Args:
            credentials: GraphQL credentials (from login_and_extract_credentials)
            target_username: Instagram username to parse
            max_reels: Maximum number of reels to fetch (None = all)

        Returns:
            list[dict]: List of reels with metrics (url, views, likes, comments, er)

        Raises:
            AuthUnexpectedError: If parsing fails
        """
        try:
            profile_link = (
                f"{self.config.parsing.instagram_url}{target_username}"
            )

            logger.bind(target=target_username, max_reels=max_reels).info(
                "Starting to parse reels"
            )

            # Fetch all reels with pagination
            reels = await fetch_all_instagram_reels(
                credentials=credentials,
                config=self.config,
                max_reels=max_reels,
                profile_link=profile_link,
                proxy_manager=self.proxy_manager,
            )

            logger.bind(target=target_username, total_reels=len(reels)).info(
                "Completed parsing reels"
            )

            return reels

        except Exception as exc:
            logger.bind(
                error_message=exc,
                target=target_username,
            ).exception("Failed to parse reels")
            raise AuthUnexpectedError(
                f"Parsing failed for {target_username}: {exc}"
            )

    async def full_workflow(
        self,
        page: Page,
        ctx: BrowserContext,
        auth: InstagramAuth,
        target_username: str,
        max_reels: int | None = None,
    ) -> tuple[dict, list[dict]]:
        """
        Complete workflow: login → extract credentials → parse reels.

        This is a convenience method that combines all steps.

        Args:
            page: Playwright page instance
            ctx: Browser context
            auth: Authentication credentials
            target_username: Profile to parse
            max_reels: Maximum reels to fetch

        Returns:
            tuple: (credentials, reels)
        """
        # Step 1: Login and extract credentials
        credentials = await self.login_and_extract_credentials(page, ctx, auth)

        # Step 2: Parse reels
        reels = await self.parse_profile_reels(
            credentials=credentials,
            target_username=target_username,
            max_reels=max_reels,
        )

        return credentials, reels
