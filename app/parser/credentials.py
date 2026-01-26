import json

from loguru import logger
from playwright.async_api import BrowserContext, Page

from app.core import Config
from app.exceptions import AuthUnexpectedError
from app.models import InstagramAuth


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
        await page.wait_for_timeout(cfg.timeouts.connection_timeout * 1000)

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

    except Exception as e:
        logger.bind(login=auth.login).error("Failed to extract credentials")
        raise AuthUnexpectedError(
            f"Credential extraction failed for {auth.login}: {e}"
        )
