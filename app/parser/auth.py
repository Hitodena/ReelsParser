import asyncio

from loguru import logger
from playwright.async_api import BrowserContext, Page, expect

from app.core import Config
from app.exceptions import AuthCredentialsError, AuthUnexpectedError
from app.models import InstagramAuth

# === Helper Functions ===


async def _check_if_already_logged_in(
    page: Page, ctx: BrowserContext, auth: InstagramAuth, cfg: Config
) -> dict | None:
    """
    Check if the user is already logged in by navigating to the login page.

    If the URL redirects to the main Instagram page, it means the user is logged in,
    and we return the existing cookies. Otherwise, return None.

    Args:
        page (Page): Playwright page instance
        ctx (BrowserContext): Playwright context instance
        auth (InstagramAuth): InstagramAuth object containing login credentials
        cfg (Config): Config object with URLs and timeouts

    Returns:
        dict | None: Dictionary of cookie name-value pairs if logged in, None otherwise
    """
    await page.goto(cfg.parsing.instagram_login_url)
    await page.wait_for_load_state("domcontentloaded")

    if page.url == cfg.parsing.instagram_url:
        logger.bind(login=auth.login).info("Already logged in, skipping auth")
        cookies = await ctx.cookies()
        return {cookie.get("name"): cookie.get("value") for cookie in cookies}
    return None


async def _attempt_old_layout_login(
    page: Page, auth: InstagramAuth, cfg: Config
) -> bool:
    """
    Attempt login using the old Instagram login layout.

    This method tries to fill the username and password fields using role-based selectors
    and clicks the login button. It includes delays between actions to mimic human behavior.

    Args:
        page (Page): Playwright page instance
        auth (InstagramAuth): InstagramAuth object with login credentials
        cfg (Config): Config object with selectors and timeouts

    Returns:
        bool: True if login attempt succeeded (no exception), False otherwise
    """
    try:
        logger.bind(login=auth.login).info("Trying old layout")

        # Locate and fill username field
        email_field = page.get_by_role(
            "textbox", name=cfg.identifiers.old_field_username_selector
        )
        await expect(email_field).to_be_editable(
            timeout=cfg.timeouts.timeout_for_element_state * 1000
        )
        logger.bind(
            login=auth.login,
            selector=cfg.identifiers.old_field_username_selector,
        ).debug("Filling username")
        await email_field.fill(auth.login)
        await asyncio.sleep(cfg.network.sleep_between_actions)

        # Locate and fill password field
        password_field = page.get_by_role(
            "textbox", name=cfg.identifiers.old_field_password_selector
        )
        logger.bind(
            login=auth.login,
            password=auth.password,
            selector=cfg.identifiers.old_field_password_selector,
        ).debug("Filling password")
        await password_field.fill(auth.password.get_secret_value())
        await asyncio.sleep(cfg.network.sleep_between_actions)

        # Click login button
        logger.bind(
            login=auth.login, selector=cfg.identifiers.old_field_login_selector
        ).debug("Clicking login button")
        await page.get_by_role(
            "button", name=cfg.identifiers.old_field_login_selector, exact=True
        ).click(
            timeout=cfg.timeouts.timeout_element * 1000, no_wait_after=False
        )
        await asyncio.sleep(cfg.network.sleep_between_actions)
        return True
    except Exception as exc:
        logger.bind(login=auth.login, error_message=exc).info(
            "Old layout failed"
        )
        return False


async def _attempt_new_layout_login(
    page: Page, auth: InstagramAuth, cfg: Config
) -> bool:
    """
    Attempt login using the new Instagram login layout.

    This method uses label-based selectors to fill username and password,
    then clicks the login button. Includes delays to avoid detection.

    Args:
        page (Page): Playwright page instance
        auth (InstagramAuth): InstagramAuth object with login credentials
        cfg (Config): Config object with selectors and timeouts

    Returns:
        bool: True if login attempt succeeded (no exception), False otherwise
    """
    try:
        logger.bind(login=auth.login).info("Trying new layout")

        # Fill username using label selector
        email_field = page.get_by_label(
            cfg.identifiers.new_field_username_selector
        )
        logger.bind(
            login=auth.login,
            selector=cfg.identifiers.new_field_username_selector,
        ).debug("Filling username")
        await email_field.fill(auth.login)
        await asyncio.sleep(cfg.network.sleep_between_actions)

        # Fill password using label selector
        password_field = page.get_by_label(
            cfg.identifiers.new_field_password_selector
        )
        logger.bind(
            login=auth.login,
            password=auth.password,
            selector=cfg.identifiers.new_field_password_selector,
        ).debug("Filling password")
        await password_field.fill(auth.password.get_secret_value())
        await asyncio.sleep(cfg.network.sleep_between_actions)

        # Click login button
        logger.bind(
            login=auth.login, selector=cfg.identifiers.new_field_login_selector
        ).debug("Clicking login button")
        await page.get_by_role(
            "button", name=cfg.identifiers.new_field_login_selector, exact=True
        ).click(
            timeout=cfg.timeouts.timeout_element * 1000, no_wait_after=False
        )
        await asyncio.sleep(cfg.network.sleep_between_actions)
        return True
    except Exception as exc:
        logger.bind(login=auth.login, error_message=exc).info(
            "New layout failed"
        )
        return False


async def _handle_additional_login_steps(
    page: Page, auth: InstagramAuth, cfg: Config
) -> None:
    """
    Handle additional login verification steps that may appear after initial login.

    Some accounts require extra confirmation, like entering password again or
    clicking continue. This function checks for and handles these steps.

    Args:
        page (Page): Playwright page instance
        auth (InstagramAuth): InstagramAuth object with credentials
        cfg (Config): Config object with selectors

    Returns:
        None
    """
    try:
        # Check for continue button (additional verification)
        continue_button = page.get_by_label(
            cfg.identifiers.continue_button_selector, exact=True
        ).first
        await expect(continue_button).to_be_visible(
            timeout=cfg.timeouts.timeout_for_element_state * 1000
        )

        logger.bind(login=auth.login).info("Additional login step required")
        await continue_button.click(
            timeout=cfg.timeouts.timeout_element * 1000, no_wait_after=False
        )
        await asyncio.sleep(cfg.network.sleep_between_actions)

        # Fill additional password if required
        password_field = page.get_by_role(
            "textbox", name=cfg.identifiers.additional_password_selector
        )
        logger.bind(
            login=auth.login,
            selector=cfg.identifiers.additional_password_selector,
        ).debug("Filling additional password")
        await password_field.fill(auth.password.get_secret_value())
        await asyncio.sleep(cfg.network.sleep_between_actions)

        # Click additional login button
        logger.bind(
            login=auth.login,
            selector=cfg.identifiers.additional_login_selector,
        ).debug("Clicking additional login button")
        await page.get_by_role(
            "button",
            name=cfg.identifiers.additional_login_selector,
            exact=True,
        ).click(
            timeout=cfg.timeouts.timeout_element * 1000, no_wait_after=False
        )
        await asyncio.sleep(cfg.network.sleep_between_actions)
    except Exception as exc:
        logger.bind(login=auth.login, error_message=exc).info(
            "No additional login steps"
        )


async def _handle_save_info(
    page: Page, auth: InstagramAuth, cfg: Config
) -> None:
    """
    Handle the "Save Info" prompt that appears after successful login.

    Instagram sometimes asks to save login info for future visits.
    This function clicks the save button if it appears.

    Args:
        page (Page): Playwright page instance
        auth (InstagramAuth): InstagramAuth object
        cfg (Config): Config object with selectors

    Returns:
        None
    """
    try:
        # Check for save info button
        save_button = page.get_by_role(
            "button", name=cfg.identifiers.save_button_selector, exact=True
        )
        await expect(save_button).to_be_visible(
            timeout=cfg.timeouts.timeout_for_element_state * 1000
        )
        logger.bind(
            login=auth.login, selector=cfg.identifiers.save_button_selector
        ).debug("Clicking save info")
        await save_button.click()
    except Exception as exc:
        logger.bind(login=auth.login, error_message=exc).info(
            "No save info button"
        )


# === Main Login Function ===


async def login_to_instagram(
    page: Page, ctx: BrowserContext, auth: InstagramAuth, cfg: Config
) -> dict:
    """
    Main function to log into Instagram and retrieve session cookies.

    This function orchestrates the entire login process:
    1. Check if already logged in
    2. Attempt login with old layout, fallback to new layout
    3. Check for login errors
    4. Handle additional verification steps
    5. Handle save info prompt
    6. Retrieve and validate cookies

    Args:
        page (Page): Playwright page instance
        ctx (BrowserContext): Browser context for cookie management
        auth (InstagramAuth): User authentication credentials
        cfg (Config): Configuration with URLs, selectors, and timeouts

    Returns:
        dict: Dictionary of cookie name-value pairs

    Raises:
        AuthCredentialsError: If login fails due to invalid credentials or missing session
        AuthUnexpectedError: For unexpected errors during login
    """
    try:
        # Step 1: Check if user is already logged in
        if cookies := await _check_if_already_logged_in(page, ctx, auth, cfg):
            return cookies

        logger.bind(login=auth.login).info("Logging into instagram")

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
