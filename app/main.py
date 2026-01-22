import asyncio
import json
from typing import AsyncGenerator
from urllib.parse import parse_qs

import httpx
from loguru import logger
from playwright.async_api import Request, expect

from .core import load
from .services import BrowserManager

config = load()


async def login_to_instagram(username, password):
    browser = BrowserManager(config)
    await browser.start()
    async with browser.context() as (page, ctx):
        with open("cookies.json", "r") as file:
            logger.info("Adding cookies")
            await ctx.add_cookies(json.load(file))
        await page.goto(config.parsing.instagram_login_url)
        logger.info("Logging in")
        textbox_email = page.get_by_role(
            "textbox", name="Phone number, username, or email"
        )
        textbox_password = page.get_by_role("textbox", name="Password")
        login_button = page.get_by_role("button", name="Log in", exact=True)
        try:
            await expect(textbox_email).to_be_editable()
            await textbox_email.fill(username)
            await asyncio.sleep(2)
            await textbox_password.fill(username)
            await login_button.click()
            await page.wait_for_load_state("load")
            await asyncio.sleep(2)
            if await page.get_by_text(
                "We couldn't connect to Instagram. Make sure you're connected to the internet and try again.",
                exact=False,
            ).is_visible():
                logger.info("Invalid credentials or network error")
            if await page.get_by_text(
                "Sorry, your password was incorrect. Please double-check your password."
            ).is_visible():
                logger.info("Invalid credentials")
                return None

        except Exception:
            logger.info("Old menu is not loaded")

        email_field = page.get_by_label("Mobile number, username or email")
        password_field = page.get_by_label("Password")
        logger.info("Filling email")
        await email_field.fill(username)
        await asyncio.sleep(2)
        logger.info("Filling password")
        await password_field.fill(password)
        await asyncio.sleep(2)
        await page.get_by_role("button", name="Log in", exact=True).click()
        await page.wait_for_load_state("load")
        await asyncio.sleep(2)
        error_element = page.get_by_text(
            "The login information you entered is incorrect.", exact=False
        )
        is_visible = await error_element.is_visible()
        logger.info(f"Error message visible: {is_visible}")
        if is_visible:
            logger.info("Wrong credentials")
            return None
        continue_button = page.get_by_label("Continue", exact=True).first
        try:
            await expect(continue_button).to_be_visible()
            logger.info("Additional log in...")
            await continue_button.click()
            password_field = page.get_by_role("textbox", name="Password")
            logger.info("Filling password")
            await password_field.fill(password)
            await page.get_by_role("button", name="Log In", exact=True).click()
        except Exception:
            logger.info("Addition log in is not needed")
        save_info_button = page.get_by_role(
            "button", name="Save info", exact=True
        )
        try:
            await expect(save_info_button).to_be_attached()
            await page.get_by_role("button", name="Save info").click()
            logger.info("Clicked save info")
        except Exception:
            logger.info("Save info is not presented")

        cookies = await ctx.cookies()
        input("Press Enter")
        with open("cookies.json", "w") as f:
            json.dump(cookies, f, ensure_ascii=False, indent=2)


async def extract_instagram_credentials(username):
    captured_data = {}

    async def intercept_request(request: Request):
        nonlocal captured_data
        if (
            request.method == "POST"
            and config.dentifiers.graph_ql_identity in request.url
            and request.post_data
            and config.dentifiers.reels_graph_ql_identity in request.post_data
        ):
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

    browser = BrowserManager(config)
    await browser.start()
    async with browser.context() as (page, context):
        page.on("request", intercept_request)

        await page.goto(f"https://www.instagram.com/{username}/reels/")

        await page.pause()

        await page.wait_for_timeout(5000)

        cookies = await context.cookies()
        for cookie in cookies:
            captured_data["cookies"][cookie.get("name", None)] = cookie.get(
                "value", None
            )

    return captured_data


async def fetch_instagram_reels(data: dict, client: httpx.AsyncClient) -> dict:
    """
    Fetches Instagram Reels data using the provided credentials and parameters.

    Args:
        data (dict): Dictionary containing doc_id, variables, headers, and cookies.
        client (httpx.AsyncClient): Reusable HTTP client.

    Returns:
        dict: JSON response from the Instagram GraphQL API.
    """
    url = "https://www.instagram.com/graphql/query"

    headers = data.get("headers", {})
    cookies = data.get("cookies", {})

    form_data = {
        k: v for k, v in data.items() if k not in ["headers", "cookies"]
    }

    if "variables" in form_data:
        form_data["variables"] = json.dumps(form_data["variables"])

    response = await client.post(
        url, data=form_data, headers=headers, cookies=cookies, timeout=30.0
    )
    response.raise_for_status()
    return response.json()


def parse_instagram_data(data: dict) -> list[dict]:
    """
    Parses Instagram GraphQL response and extracts Reels data.

    Args:
        data (dict): GraphQL response.

    Returns:
        list[dict]: List of parsed reels with url, views, likes, comments, ER.
    """
    reels = []
    edges = data["data"]["xdt_api__v1__clips__user__connection_v2"]["edges"]

    for edge in edges:
        node = edge["node"]["media"]
        views = node["play_count"]
        likes = node["like_count"]
        comments = node["comment_count"]

        er = ((likes + comments) / views) if views > 0 else 0

        reels.append(
            {
                "url": f"https://www.instagram.com/reel/{node['code']}/",
                "views": views,
                "likes": likes,
                "comments": comments,
                "er": round(er, 3),
            }
        )

    return reels


async def fetch_all_instagram_reels(
    credentials: dict,
    max_reels: int | None = None,
    delay: float = 1.0,
    max_retries: int = 3,
) -> list[dict]:
    """
    Fetches all Instagram Reels with pagination and error handling.

    Args:
        credentials (dict): Initial credentials from extract_instagram_credentials.
        max_reels (int | None): Maximum number of reels to fetch. None = all.
        delay (float): Delay between requests in seconds.
        max_retries (int): Maximum number of retries on failure.

    Returns:
        list[dict]: List of all reels with ER calculated.
    """
    all_reels = []
    has_next = True
    cursor = None

    data = json.loads(json.dumps(credentials))

    async with httpx.AsyncClient() as client:
        while has_next:
            retries = 0

            while retries < max_retries:
                try:
                    if cursor:
                        data["variables"]["after"] = cursor

                    response = await fetch_instagram_reels(data, client)

                    reels = parse_instagram_data(response)
                    all_reels.extend(reels)

                    page_info = response["data"][
                        "xdt_api__v1__clips__user__connection_v2"
                    ]["page_info"]
                    has_next = page_info["has_next_page"]
                    cursor = page_info["end_cursor"]

                    if max_reels and len(all_reels) >= max_reels:
                        return all_reels[:max_reels]

                    if has_next:
                        await asyncio.sleep(delay)

                    break

                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 429:
                        # Rate limit
                        wait_time = 60 * (retries + 1)
                        await asyncio.sleep(wait_time)
                        retries += 1
                    else:
                        raise

                except (httpx.TimeoutException, httpx.NetworkError) as exc:
                    retries += 1
                    if retries >= max_retries:
                        raise
                    await asyncio.sleep(delay * retries)

    return all_reels


async def stream_instagram_reels(
    credentials: dict, delay: float = 1.0
) -> AsyncGenerator[dict, None]:
    """
    Streams Instagram Reels one by one (memory efficient).

    Args:
        credentials (dict): Initial credentials.
        delay (float): Delay between requests.

    Yields:
        dict: Individual reel data.
    """
    has_next = True
    cursor = None
    data = json.loads(json.dumps(credentials))

    async with httpx.AsyncClient() as client:
        while has_next:
            if cursor:
                data["variables"]["after"] = cursor

            response = await fetch_instagram_reels(data, client)
            reels = parse_instagram_data(response)

            for reel in reels:
                yield reel

            page_info = response["data"][
                "xdt_api__v1__clips__user__connection_v2"
            ]["page_info"]
            has_next = page_info["has_next_page"]
            cursor = page_info["end_cursor"]

            if has_next:
                await asyncio.sleep(delay)
