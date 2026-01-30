import json

from loguru import logger
from playwright.async_api import BrowserContext, Page, expect

from app.core import Config
from app.exceptions import (
    AuthUnexpectedError,
    UserNotFoundError,
    UserPrivateError,
)
from app.models import InstagramAuth


async def extract_credentials_with_followers(
    page: Page,
    ctx: BrowserContext,
    auth: InstagramAuth,
    cfg: Config,
    target_username: str,
) -> tuple[dict, int]:
    """
    Extract GraphQL credentials and followers count by intercepting Instagram API requests.

    This function loads cookies, navigates to the user's reels page, captures
    the necessary headers, variables, and updated cookies from GraphQL requests,
    and extracts the followers count from the page.

    Args:
        page: Playwright page instance
        ctx: Browser context for cookie management
        auth: InstagramAuth object with login and cookies
        cfg: Configuration object with URLs and identifiers
        target_username: Target username to extract followers for

    Returns:
        tuple[dict, int]: Tuple containing (credentials dict, followers count)
    """
    credentials = await extract_credentials(
        page, ctx, auth, cfg, target_username
    )

    # Extract followers count1
    try:
        followers_element = page.locator(
            cfg.identifiers.followers_selector
        ).first
        followers_text = await followers_element.get_attribute(
            "title", timeout=cfg.timeouts.timeout_element * 1000
        )
        if followers_text:
            # Extract number from title, e.g., "1,234 followers" -> 1234
            followers_count = int("".join(filter(str.isdigit, followers_text)))
        else:
            followers_count = 0
    except Exception as exc:
        logger.bind(login=auth.login, target_username=target_username).warning(
            f"Failed to extract followers count: {exc}"
        )
        followers_count = 0

    return credentials, followers_count


async def extract_credentials(
    page: Page,
    ctx: BrowserContext,
    auth: InstagramAuth,
    cfg: Config,
    target_username: str,
) -> dict:
    """
    Extract GraphQL credentials by intercepting Instagram API requests.

    This function loads cookies, navigates to the user's reels page, and captures
    the necessary headers, variables, and updated cookies from GraphQL requests.

    Args:
        page: Playwright page instance
        ctx: Browser context for cookie management
        auth: InstagramAuth object with login and cookies
        cfg: Configuration object with URLs and identifiers

    Returns:
        dict: Dictionary containing doc_id, variables, headers, and cookies
    """
    captured_data = {}

    async def intercept_request(request):
        nonlocal captured_data
        if (
            request.method == "POST"
            and cfg.identifiers.graph_ql_identity in request.url
            and request.post_data
            and cfg.identifiers.reels_graph_ql_identity in request.post_data
        ):
            from urllib.parse import parse_qs

            post_data = parse_qs(request.post_data)

            captured_data = {
                "doc_id": post_data.get("doc_id", [None])[0],
                "variables": json.loads(post_data.get("variables", ["{}"])[0]),
                "headers": {
                    "X-CSRFToken": request.headers.get("x-csrftoken"),
                    "X-IG-App-ID": request.headers.get("x-ig-app-id"),
                    "X-FB-LSD": request.headers.get("x-fb-lsd"),
                    "X-ASBD-ID": request.headers.get("x-asbd-id"),
                    "X-FB-Friendly-Name": request.headers.get(
                        "x-fb-friendly-name"
                    ),
                    "User-Agent": request.headers.get("user-agent"),
                    "X-BLOKS-VERSION-ID": request.headers.get(
                        "x-bloks-version-id"
                    ),
                    "X-Root-Field-Name": request.headers.get(
                        "x-root-field-name"
                    ),
                },
                "cookies": {},
            }

    try:
        if not auth.cookies:
            raise AuthUnexpectedError(
                f"No cookies provided for credential extraction for {auth.login}"
            )

        # Load initial cookies into browser context
        cookies_list = [
            {
                "name": k,
                "value": v,
                "domain": ".instagram.com",
                "path": "/",
            }
            for k, v in auth.cookies.items()
        ]
        await ctx.add_cookies(cookies_list)  # type: ignore

        # Set up request interception
        page.on("request", intercept_request)

        # Navigate to reels page to trigger GraphQL requests
        logger.bind(login=auth.login).info("Extracting credentials")
        await page.goto(
            f"{cfg.parsing.instagram_url}{target_username}{cfg.parsing.instagram_reels_url}/"
        )
        await page.wait_for_load_state("domcontentloaded")

        # Check for error texts
        try:
            await expect(
                page.get_by_text(cfg.identifiers.private_account_text)
            ).to_be_visible(timeout=cfg.timeouts.timeout_for_element_state)
            raise UserPrivateError(f"Account {target_username} is private")
        except AssertionError:
            pass

        try:
            await expect(
                page.get_by_text(cfg.identifiers.not_found_text)
            ).to_be_visible(timeout=cfg.timeouts.timeout_for_element_state)
            raise UserNotFoundError(f"Account {target_username} not found")
        except AssertionError:
            pass

        try:
            await expect(
                page.get_by_text(cfg.identifiers.not_found_text_alt)
            ).to_be_visible(timeout=cfg.timeouts.timeout_for_element_state)
            raise UserNotFoundError(f"Account {target_username} not found")
        except AssertionError:
            pass

        # Update cookies (they may have been refreshed)
        fresh_cookies = await ctx.cookies()
        for cookie in fresh_cookies:
            captured_data.setdefault("cookies", {})[cookie.get("name")] = (
                cookie.get("value")
            )

        if not captured_data:
            raise AuthUnexpectedError(
                f"Failed to capture GraphQL request for {auth.login}"
            )

        logger.bind(login=auth.login).info("Credentials extracted")
        return captured_data

    except UserPrivateError:
        logger.bind(login=auth.login, target_username=target_username).warning(
            "Failed to extract credentials due to account privacy"
        )
        raise
    except UserNotFoundError:
        logger.bind(login=auth.login, target_username=target_username).warning(
            "Failed to extract credentials due to account non-existing"
        )
        raise
    except Exception as exc:
        logger.bind(login=auth.login).error("Failed to extract credentials")
        raise AuthUnexpectedError(
            f"Credential extraction failed for {auth.login}: {exc}"
        )
