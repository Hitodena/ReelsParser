from loguru import logger
from playwright.async_api import BrowserContext, Page

from app.core import Config
from app.exceptions import (
    AuthCredentialsError,
    AuthUnexpectedError,
    ProxyForbiddenError,
    ProxyTooManyAttemptsError,
    ProxyUnexpectedError,
    UserNotFoundError,
    UserPrivateError,
)
from app.models import InstagramAuth
from app.parser import (
    extract_credentials_with_followers,
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

    async def check_account_login(
        self, page: Page, ctx: BrowserContext, auth: InstagramAuth
    ) -> dict:
        """Get cookies to DB model account

        Args:
            page (Page): Playwright page instance
            ctx (BrowserContext): Browser context
            auth (InstagramAuth): Authentication credentials

        Raises:
            AuthCredentialsError: If login fails due to invalid credentials
            AuthUnexpectedError: For unexpected errors
        """
        try:
            logger.bind(login=auth.login).info("Starting login")
            cookies = await login_to_instagram(page, ctx, auth, self.config)
            logger.bind(login=auth.login).info(
                "Successfully logged and returned cookies"
            )

            return cookies
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

    async def login_and_extract_credentials(
        self,
        page: Page,
        ctx: BrowserContext,
        auth: InstagramAuth,
        target_username: str,
    ) -> tuple[dict, int]:
        """
        Login to Instagram and extract GraphQL credentials with followers count.

        Args:
            page: Playwright page instance
            ctx: Browser context
            auth: Authentication credentials (login + password OR cookies)
            target_username: Target username to extract followers for

        Returns:
            tuple[dict, int]: Tuple containing (credentials dict, followers count)

        Raises:
            AuthCredentialsError: If login fails due to invalid credentials
            AuthUnexpectedError: For unexpected errors
            UserPrivateError: If the target user account is private
            UserNotFoundError: If the target user is not found
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

            # Step 2: Extract credentials and followers
            credentials, followers = await extract_credentials_with_followers(
                page, ctx, auth, self.config, target_username
            )

            logger.bind(
                login=auth.login,
                has_doc_id=bool(credentials.get("doc_id")),
                has_cookies=bool(credentials.get("cookies")),
                followers=followers,
            ).info("Successfully extracted credentials and followers")

            return credentials, followers

        except AuthCredentialsError as exc:
            logger.bind(error_message=str(exc), login=auth.login).error(
                "Invalid credentials"
            )
            raise
        except UserPrivateError as exc:
            logger.bind(error_message=str(exc), login=auth.login).error(
                "User account is private"
            )
            raise
        except UserNotFoundError as exc:
            logger.bind(error_message=str(exc), login=auth.login).error(
                "User not found"
            )
            raise
        except AuthUnexpectedError as exc:
            logger.bind(error_message=str(exc), login=auth.login).error(
                "Unexpected error during extraction"
            )
            raise
        except Exception as exc:
            logger.bind(error_message=str(exc), login=auth.login).exception(
                "Failed to extract credentials"
            )
            raise AuthUnexpectedError(
                f"Credential extraction failed for {auth.login}: {exc}"
            )

    async def parse_profile_reels(
        self,
        credentials: dict,
        target_username: str,
        followers: int,
        max_reels: int | None = None,
    ) -> list[dict]:
        """
        Parse all reels from a target profile using stored credentials.

        Args:
            credentials: GraphQL credentials (from login_and_extract_credentials)
            target_username: Instagram username to parse
            followers: Number of followers for virality calculation
            max_reels: Maximum number of reels to fetch (None = all)

        Returns:
            list[dict]: List of reels with metrics (url, views, likes, comments, er)

        Raises:
            AuthUnexpectedError: If parsing fails after all proxy attempts
        """
        all_reels: list[dict] = []
        seen_urls: set[str] = set()

        def add_unique_reels(reels: list[dict]) -> None:
            """Add only unique reels (by URL) to all_reels."""
            for reel in reels:
                url = reel.get("url")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    all_reels.append(reel)

        for proxy_attempt in range(
            self.config.retries.max_proxy_parsing_retries
        ):
            # Get least used proxy from manager
            proxy = await self.proxy_manager.get_least_used()
            formatted_httpx_proxy = proxy.to_httpx_proxy() if proxy else None

            try:
                logger.bind(
                    target=target_username,
                    max_reels=max_reels,
                    proxy=formatted_httpx_proxy,
                    proxy_attempt=proxy_attempt + 1,
                ).info("Starting to parse reels")

                # Fetch all reels with pagination
                reels = await fetch_all_instagram_reels(
                    followers=followers,
                    credentials=credentials,
                    config=self.config,
                    max_reels=max_reels,
                    target_username=target_username,
                    formatted_httpx_proxy=formatted_httpx_proxy,
                )

                # Success - mark proxy as used and return
                if proxy:
                    await self.proxy_manager.mark_used(proxy.identifier)

                logger.bind(
                    target=target_username, total_reels=len(reels)
                ).info("Completed parsing reels")

                return reels

            except ProxyForbiddenError as exc:
                # 403 - block proxy immediately and try next
                logger.bind(
                    error_message=str(exc),
                    target=target_username,
                    proxy=formatted_httpx_proxy,
                ).warning("Proxy forbidden, blocking and trying next")
                if proxy:
                    await self.proxy_manager.block_proxy(proxy.identifier, 120)
                add_unique_reels(exc.partial_results)
                continue

            except ProxyTooManyAttemptsError as exc:
                # 429 after retries - block proxy and try next
                logger.bind(
                    error_message=str(exc),
                    target=target_username,
                    proxy=formatted_httpx_proxy,
                ).warning("Proxy rate limited, blocking and trying next")
                if proxy:
                    await self.proxy_manager.block_proxy(proxy.identifier, 20)
                add_unique_reels(exc.partial_results)
                continue

            except ProxyUnexpectedError as exc:
                # Network error after retries - try next proxy
                logger.bind(
                    error_message=str(exc),
                    target=target_username,
                    proxy=formatted_httpx_proxy,
                ).warning("Proxy network error, trying next")
                add_unique_reels(exc.partial_results)
                continue

        # All proxy attempts exhausted - return partial results
        logger.bind(
            target=target_username,
            total_reels=len(all_reels),
            max_proxy_retries=self.config.retries.max_proxy_parsing_retries,
        ).warning("All proxy attempts exhausted, returning partial results")

        return all_reels

    async def full_workflow(
        self,
        page: Page,
        ctx: BrowserContext,
        auth: InstagramAuth,
        target_username: str,
        max_reels: int | None = None,
    ) -> tuple[list[dict], dict]:
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
            tuple: (reels, credentials)
        """
        # Step 1: Login and extract credentials
        credentials, followers = await self.login_and_extract_credentials(
            page, ctx, auth, target_username
        )

        # Step 2: Parse reels
        reels = await self.parse_profile_reels(
            credentials=credentials,
            target_username=target_username,
            max_reels=max_reels,
            followers=followers,
        )

        return reels, credentials
