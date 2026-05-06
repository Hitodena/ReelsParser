import argparse
import asyncio
import sys

from loguru import logger
from playwright.async_api import BrowserContext, Page

from app.core import load
from app.db.dao import InstagramAccountDAO
from app.exceptions import AuthCredentialsError, AuthUnexpectedError
from app.models import InstagramAuth
from app.parser.auth import (
    _attempt_new_layout_login,
    _attempt_old_layout_login,
    _check_if_already_logged_in,
    _handle_additional_login_steps,
    _handle_save_info,
)
from app.services import (
    BrowserManager,
    DatabaseSessionManager,
    ProxyManager,
    RedisManager,
)


async def manual_login_to_instagram(
    page: Page, ctx: BrowserContext, auth: InstagramAuth, cfg
) -> dict:
    """
    Modified login function that pauses after submitting credentials for manual popup handling.

    Args:
        page: Playwright page instance
        ctx: Browser context
        auth: Authentication credentials
        cfg: Config

    Returns:
        dict: Cookies dict

    Raises:
        AuthCredentialsError: Invalid credentials
        AuthUnexpectedError: Unexpected errors
    """

    try:
        # Step 1: Navigate to Instagram (may return non-2xx, handle gracefully)
        logger.info(f"Navigating to {cfg.parsing.instagram_login_url}")
        try:
            response = await page.goto(
                cfg.parsing.instagram_login_url,
                wait_until="domcontentloaded",
                timeout=30000
            )
            if response:
                logger.info(f"Navigation response status: {response.status}")
                if response.status >= 400:
                    logger.warning(f"Instagram returned status {response.status}, continuing anyway...")
            else:
                logger.warning("No response object from page.goto (navigation may have failed)")
        except Exception as nav_exc:
            logger.warning(f"Navigation error (may be expected): {nav_exc}")
            # Check if page is actually on an error page - we can still try to interact
            current_url = page.url
            logger.info(f"Current URL after navigation attempt: {current_url}")

        # Step 1 alt: Check if already logged in
        if cookies := await _check_if_already_logged_in(page, ctx, auth, cfg):
            return cookies

        logger.bind(login=auth.login).info("Logging into Instagram")

        # Step 2: Attempt login with different layouts
        if not await _attempt_old_layout_login(page, auth, cfg):
            await _attempt_new_layout_login(page, auth, cfg)

        # Wait for page to load after login attempt
        await page.wait_for_load_state("load")
        await asyncio.sleep(cfg.network.sleep_between_actions)

        # Step 3: Check for login error messages
        for error_text in cfg.identifiers.error_texts:
            error_message = page.get_by_text(error_text, exact=False)
            if await error_message.is_visible(
                timeout=cfg.timeouts.timeout_for_element_state * 1000
            ):
                logger.bind(login=auth.login, error_message=error_text).error(
                    "Login failed"
                )
                raise AuthCredentialsError(f"Login failed: {error_text}")

        # MANUAL INTERVENTION: Pause here for user to handle email confirmation popup
        print("\n" + "=" * 60)
        print("LOGIN SUBMITTED SUCCESSFULLY!")
        print(
            "Please check your email and handle the confirmation popup manually."
        )
        print("Once you've confirmed the email and the popup is resolved,")
        print("press Enter to continue with cookie extraction...")
        print("=" * 60)
        input()

        logger.bind(login=auth.login).info(
            "Resuming after manual confirmation"
        )

        # Step 4: Handle additional login verification if required
        await _handle_additional_login_steps(page, auth, cfg)

        # Step 5: Handle save info prompt
        await _handle_save_info(page, auth, cfg)

        # Step 6: Retrieve and validate cookies
        cookies = await ctx.cookies()
        cookies_dict = {c.get("name"): c.get("value") for c in cookies}

        if not cookies_dict.get("sessionid"):
            raise AuthCredentialsError("No sessionid in cookies")

        logger.bind(login=auth.login).info("Successfully logged in")
        return cookies_dict

    except AuthCredentialsError:
        raise
    except Exception as exc:
        logger.bind(login=auth.login).exception("Login failed")
        raise AuthUnexpectedError(f"Login failed: {exc}")


async def main(login: str, password: str):
    """Main registration function."""
    try:
        # Load configuration
        config = load()

        # Initialize services
        db_manager = DatabaseSessionManager(config.environment.get_db_url())
        redis_manager = RedisManager(config.environment.redis_url)

        await redis_manager.connect()
        db_manager.init()

        if not redis_manager.redis:
            raise RuntimeError("Redis is not initialized")

        proxy_manager = ProxyManager(redis_manager.redis, config)
        browser_manager = BrowserManager(config)
        await browser_manager.start()

        logger.info("Services initialized successfully")

        auth = InstagramAuth(login=login, password=password)

        # Check if account already exists
        async with db_manager.session() as session:
            existing = await InstagramAccountDAO.get_by_login(session, login)
        if existing:
            logger.error(f"Account '{login}' already exists")
            return

        # Get least used proxy
        proxy_formatted = None
        proxy = await proxy_manager.get_least_used()
        if proxy:
            proxy_formatted = proxy.to_playwright_proxy()
            logger.info(f"Using proxy: {proxy.identifier}")
        else:
            logger.warning("No proxy available, proceeding without proxy")

        # Manual login with browser context
        async with browser_manager.context(proxy=proxy_formatted) as (
            page,
            ctx,
        ):
            logger.info("Browser context created, starting manual login")

            # Navigate to Instagram
            await page.goto(config.parsing.instagram_login_url)

            # Perform manual login
            cookies = await manual_login_to_instagram(page, ctx, auth, config)

            logger.info("Cookies extracted successfully")

        # Save to database
        async with db_manager.session() as session:
            await InstagramAccountDAO.add(
                session,
                login=login,
                password=password,
                cookies=cookies,
                valid=True,
            )

        logger.success(
            f"Account '{login}' registered successfully with {len(cookies)} cookies"
        )

    except AuthCredentialsError as exc:
        logger.error(
            f"Registration failed for '{login}': Invalid credentials - {exc}"
        )
        sys.exit(1)
    except AuthUnexpectedError as exc:
        logger.error(
            f"Registration failed for '{login}': Unexpected error - {exc}"
        )
        sys.exit(1)
    except Exception as exc:
        logger.exception(f"Registration failed for '{login}': {exc}")
        sys.exit(1)
    finally:
        # Cleanup
        try:
            await redis_manager.close()  # type: ignore
            await browser_manager.close()  # type: ignore
            await db_manager.close()  # type: ignore
        except Exception:
            pass


def main_cli():
    """Command line interface."""
    parser = argparse.ArgumentParser(
        description="Manually register an Instagram account with email confirmation handling.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
            This script will:
            1. Submit login credentials to Instagram
            2. Pause for manual email confirmation
            3. Extract session cookies after confirmation
            4. Save the account to the database
            """,
    )
    parser.add_argument("login", help="Instagram login/username")
    parser.add_argument("password", help="Instagram password")

    args = parser.parse_args()

    logger.info(f"Starting manual registration for '{args.login}'")
    asyncio.run(main(args.login, args.password))


if __name__ == "__main__":
    main_cli()
