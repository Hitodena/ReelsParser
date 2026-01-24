import asyncio
import json
import random
import time

import httpx
from loguru import logger

from app.core import Config


async def fetch_instagram_reels(
    data: dict, client: httpx.AsyncClient, config: Config, profile_link: str
) -> dict:
    """
    Fetches Instagram Reels data using the provided credentials and parameters.

    Args:
        data (dict): Dictionary containing doc_id, variables, headers, and cookies.
        client (httpx.AsyncClient): Reusable HTTP client.
        config (Config): Config object.


    Returns:
        dict: JSON response from the Instagram GraphQL API.
    """
    url = config.parsing.api_instagram_reels_url

    headers = data.get("headers", {})
    cookies = data.get("cookies", {})

    # Set data for POST
    form_data = {
        k: v for k, v in data.items() if k not in ["headers", "cookies"]
    }

    # Set variables
    if "variables" in form_data:
        form_data["variables"] = json.dumps(form_data["variables"])

    start_time = time.perf_counter()
    logger.bind(profile_link=profile_link, url=url).info(
        "Fetching Instagram reels"
    )
    response = await client.post(
        url,
        data=form_data,
        headers=headers,
        cookies=cookies,
        timeout=config.timeouts.connection_timeout,
    )
    elapsed_time = time.perf_counter() - start_time
    response.raise_for_status()
    logger.bind(
        profile_link=profile_link,
        url=url,
        execution_time=f"{elapsed_time:.2f}",
    ).success("Fetched Instagram reels successfully")
    return response.json()


def parse_instagram_data(data: dict, profile_link: str) -> list[dict]:
    """
    Parses Instagram GraphQL response and extracts Reels data.

    Args:
        data (dict): GraphQL response.
        profile_link (str): Profile link for logging.

    Returns:
        list[dict]: List of parsed reels with url, views, likes, comments, ER.
    """
    reels = []
    edges = data["data"]["xdt_api__v1__clips__user__connection_v2"]["edges"]
    logger.bind(profile_link=profile_link, edges_count=len(edges)).info(
        "Parsing Instagram data"
    )

    # Find main info
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

    logger.bind(profile_link=profile_link, count=len(reels)).success(
        "Parsed reels"
    )
    return reels


async def fetch_all_instagram_reels(
    credentials: dict, config: Config, max_reels: int | None, profile_link: str
) -> list[dict]:
    """
    Fetches all Instagram Reels with pagination and error handling.

    Args:
        credentials (dict): Initial credentials from extract_instagram_credentials.
        profile_link (str): Profile link for logging.

    Returns:
        list[dict]: List of all reels with ER calculated.
    """
    max_retries = config.retries.max_retries
    logger.bind(
        profile_link=profile_link, max_reels=max_reels, max_retries=max_retries
    ).info("Starting to fetch all Instagram reels")
    all_reels = []
    has_next = True
    cursor = None

    # Load data from data (cookies, headers, data)
    data = json.loads(json.dumps(credentials))

    try:
        async with httpx.AsyncClient() as client:
            while has_next:
                retries = 0

                while retries < max_retries:
                    try:
                        # Set cursor to have pagination control
                        if cursor:
                            data["variables"]["after"] = cursor

                        response = await fetch_instagram_reels(
                            data, client, config, profile_link
                        )

                        reels = parse_instagram_data(response, profile_link)
                        all_reels.extend(reels)

                        page_info = response["data"][
                            "xdt_api__v1__clips__user__connection_v2"
                        ]["page_info"]
                        has_next = page_info["has_next_page"]
                        cursor = page_info["end_cursor"]

                        if max_reels and len(all_reels) >= max_reels:
                            return all_reels[:max_reels]

                        if has_next:
                            await asyncio.sleep(
                                random.uniform(
                                    config.network.sleep_between_requests_min,
                                    config.network.sleep_between_requests_max,
                                )
                            )

                        break

                    except httpx.HTTPStatusError as e:
                        if e.response.status_code == 429:
                            # Rate limit
                            wait_time = config.network.rate_limit_wait_base * (
                                config.network.backoff_factor**retries
                            )
                            logger.bind(
                                status_code=e.response.status_code,
                                wait_time=wait_time,
                                retries=retries,
                            ).warning("Rate limit hit")
                            await asyncio.sleep(wait_time)
                            retries += 1
                        else:
                            raise

                    except (httpx.TimeoutException, httpx.NetworkError) as exc:
                        retries += 1
                        logger.bind(
                            retries=retries,
                            max_retries=max_retries,
                            error=str(exc),
                        ).warning("Network error, retrying")
                        if retries >= max_retries:
                            raise
                        await asyncio.sleep(
                            config.network.sleep_between_requests_min
                            * config.network.backoff_factor**retries
                        )

        logger.bind(
            profile_link=profile_link, total_reels=len(all_reels)
        ).success("Completed fetching all Instagram reels")
    except Exception as exc:
        logger.bind(
            profile_link=profile_link,
            total_reels=len(all_reels),
            error=str(exc),
        ).error(
            "Exception occurred while fetching reels, returning collected reels"
        )
    return all_reels
