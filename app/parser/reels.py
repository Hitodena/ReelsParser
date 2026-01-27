import asyncio
import json
import random
import time
from typing import TYPE_CHECKING

import httpx
from loguru import logger

from app.core import Config

if TYPE_CHECKING:
    from app.services import ProxyManager


async def fetch_instagram_reels(
    data: dict,
    client: httpx.AsyncClient,
    config: Config,
    target_username: str,
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
    logger.bind(target_username=target_username, url=url).info(
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
    delay = random.uniform(
        config.network.sleep_between_requests_min,
        config.network.sleep_between_requests_max,
    )
    logger.bind(
        target_username=target_username,
        url=url,
        execution_time=f"{elapsed_time:.2f}",
        delay=f"{delay:.2f}",
    ).info("Fetched Instagram reels successfully")
    await asyncio.sleep(delay)
    return response.json()


def parse_instagram_data(data: dict, target_username: str) -> list[dict]:
    """
    Parses Instagram GraphQL response and extracts Reels data.

    Args:
        data (dict): GraphQL response.
        profile_link (str): Profile link for logging.

    Returns:
        list[dict]: List of parsed reels with url, views, likes, comments, ER.
    """
    reels: list = []
    edges = data["data"]["xdt_api__v1__clips__user__connection_v2"]["edges"]

    # Find main info
    for edge in edges:
        node = edge["node"]["media"]
        if not isinstance(node, dict):
            logger.bind(
                target_username=target_username,
                node_type=type(node),
                edge_index=edges.index(edge),
            ).warning("Node media is not dict, skipping")
            continue
        if not all(
            key in node
            for key in ["play_count", "like_count", "comment_count", "code"]
        ):
            logger.bind(
                target_username=target_username, node_keys=list(node.keys())
            ).warning("Node missing required keys, skipping")
            continue
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
    config: Config,
    max_reels: int | None,
    target_username: str,
    proxy_manager: "ProxyManager",
) -> list[dict]:
    """
    Fetches all Instagram Reels with pagination and error handling.

    Args:
        credentials (dict): Initial credentials from extract_instagram_credentials.
        profile_link (str): Profile link for logging.
        max_reels (int): Max amount of reels to parse.
        proxy_manager (ProxyManager): Proxy manager object.

    Returns:
        list[dict]: List of all reels with ER calculated.
    """
    max_retries = config.retries.max_retries
    logger.bind(
        target_username=target_username,
        max_reels=max_reels,
        max_retries=max_retries,
    ).info("Starting to fetch all Instagram reels")
    all_reels = []
    has_next = True
    cursor = None

    # Load data from data (cookies, headers, data)
    data = json.loads(json.dumps(credentials))
    proxy = await proxy_manager.get_least_used()
    proxy_formatted = None
    if proxy:
        proxy_formatted = proxy.to_httpx_proxy()

    try:
        async with httpx.AsyncClient(proxy=proxy_formatted) as client:
            while has_next:
                if max_reels and len(all_reels) >= max_reels:
                    break
                retries = 0

                while retries < max_retries:
                    try:
                        # Set cursor to have pagination control
                        if cursor:
                            data["variables"]["after"] = cursor

                        response = await fetch_instagram_reels(
                            data, client, config, target_username
                        )

                        reels = parse_instagram_data(response, target_username)
                        if max_reels:
                            remaining = max_reels - len(all_reels)
                            all_reels.extend(reels[:remaining])
                        else:
                            all_reels.extend(reels)

                        page_info = response["data"][
                            "xdt_api__v1__clips__user__connection_v2"
                        ]["page_info"]
                        has_next = page_info["has_next_page"]
                        cursor = page_info["end_cursor"]

                        break

                    except httpx.HTTPStatusError as exc:
                        if exc.response.status_code == 429:
                            # Rate limit
                            wait_time = config.network.rate_limit_wait_base * (
                                config.network.backoff_factor**retries
                            )
                            logger.bind(
                                error_message=str(exc),
                                status_code=exc.response.status_code,
                                wait_time=wait_time,
                                retries=retries,
                            ).warning("Rate limit hit")
                            await asyncio.sleep(wait_time)
                            retries += 1
                            if proxy:
                                await proxy_manager.block_proxy(
                                    proxy.identifier, 10
                                )
                        else:
                            raise

                    except (httpx.TimeoutException, httpx.NetworkError) as exc:
                        retries += 1
                        if proxy:
                            await proxy_manager.block_proxy(
                                proxy.identifier, 60
                            )
                        logger.bind(
                            error_message=exc,
                            retries=retries,
                            max_retries=max_retries,
                        ).warning("Network error, retrying")
                        if retries >= max_retries:
                            raise
                        await asyncio.sleep(
                            config.network.sleep_between_requests_min
                            * config.network.backoff_factor**retries
                        )

        logger.bind(
            target_username=target_username, total_reels=len(all_reels)
        ).info("Completed fetching all Instagram reels")
    except Exception as exc:
        returned_reels = all_reels[:max_reels] if max_reels else all_reels
        logger.bind(
            error_message=exc,
            target_username=target_username,
            total_reels=len(returned_reels),
        ).exception(
            "Exception occurred while fetching reels, returning collected reels"
        )
    finally:
        return all_reels
