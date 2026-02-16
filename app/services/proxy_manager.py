import asyncio
import time
from datetime import timedelta

import httpx
from loguru import logger
from redis.asyncio import Redis

from app.core import Config
from app.models import ProxyModel


class ProxyManager:
    """Manages proxy operations using Redis pools for state management.

    State is managed purely through Redis:
    - Active proxies: stored in sorted set (proxy:sorted) with score as last_used timestamp
    - Blocked proxies: stored with TTL key (proxy:blocked:{id}) that auto-expires
    - Proxy data: stored as JSON (proxy:{id})
    """

    def __init__(self, redis: Redis, cfg: Config) -> None:
        """Initialize the ProxyManager with Redis client and configuration.

        Args:
            redis: Redis client instance for data storage.
            cfg: Configuration object containing timeouts, retries, etc.
        """
        self.redis = redis
        self.cfg = cfg
        self.proxy_key = "proxy:"
        self.proxy_sorted_key = f"{self.proxy_key}sorted"
        self.proxy_block_key = f"{self.proxy_key}blocked:"
        logger.info("ProxyManager initialized")

    async def add_proxy(self, proxy: ProxyModel) -> str:
        """Add a new proxy after validating it.

        Args:
            proxy: ProxyModel instance to add.

        Returns:
            Proxy identifier if added successfully.
        """
        proxy_str = proxy.to_httpx_proxy()
        is_valid = await self.validate_proxy(proxy_str)
        if not is_valid:
            logger.bind(proxy_id=proxy.identifier).warning(
                "Proxy validation failed, not adding"
            )
            return proxy.identifier

        key = f"{self.proxy_key}{proxy.identifier}"

        await self.redis.set(key, proxy.model_dump_json())

        # Add to sorted set with score 0 (newest/least used)
        await self.redis.zadd(self.proxy_sorted_key, {proxy.identifier: 0})

        logger.bind(proxy_id=proxy.identifier).info("Proxy added successfully")
        return proxy.identifier

    async def get_proxy(self, proxy_id: str) -> ProxyModel | None:
        """Retrieve a proxy by its identifier.

        Args:
            proxy_id: The unique identifier of the proxy.

        Returns:
            ProxyModel instance if found, None otherwise.
        """
        key = f"{self.proxy_key}{proxy_id}"
        data = await self.redis.get(key)

        if not data:
            logger.bind(proxy_id=proxy_id).warning("Proxy not found")
            return None

        logger.bind(proxy_id=proxy_id).info("Proxy retrieved successfully")
        return ProxyModel.model_validate_json(data)

    async def is_blocked(self, proxy_id: str) -> bool:
        """Check if a proxy is currently blocked.

        Args:
            proxy_id: The unique identifier of the proxy.

        Returns:
            True if proxy is blocked, False otherwise.
        """
        block_key = f"{self.proxy_block_key}{proxy_id}"
        return await self.redis.exists(block_key) > 0

    async def get_least_used(self) -> ProxyModel | None:
        """Get the least used active and unblocked proxy.

        Returns:
            The least used ProxyModel if available, None otherwise.
        """
        # Get all proxies from sorted set, sorted by score (last_used)
        results = await self.redis.zrange(self.proxy_sorted_key, 0, -1)

        if not results:
            logger.warning("No proxies available")
            return None

        # Find first unblocked proxy
        for proxy_id in results:
            if await self.is_blocked(proxy_id):
                logger.bind(proxy_id=proxy_id).debug("Skipping blocked proxy")
                continue

            proxy = await self.get_proxy(proxy_id)
            if proxy:
                logger.bind(proxy_id=proxy_id).info(
                    "Least used proxy selected"
                )
                return proxy

        logger.warning("No unblocked proxies available")
        return None

    async def mark_used(self, proxy_id: str) -> None:
        """Mark a proxy as used, updating its last used timestamp.

        Args:
            proxy_id: The identifier of the proxy to mark as used.
        """
        proxy = await self.get_proxy(proxy_id)

        if not proxy:
            return

        # Update score in sorted set with current timestamp

        await self.redis.zadd(self.proxy_sorted_key, {proxy_id: time.time()})
        logger.bind(proxy_id=proxy_id).info("Proxy marked as used")

    async def block_proxy(self, proxy_id: str, minutes: int = 60) -> None:
        """Block a proxy for a specified number of minutes.

        The block is stored as a Redis key with TTL, auto-expires.

        Args:
            proxy_id: The identifier of the proxy to block.
            minutes: Number of minutes to block the proxy (default 60).
        """
        block_key = f"{self.proxy_block_key}{proxy_id}"
        await self.redis.setex(block_key, timedelta(minutes=minutes), "1")
        logger.bind(proxy_id=proxy_id, minutes=minutes).info("Proxy blocked")

    async def unblock_proxy(self, proxy_id: str) -> None:
        """Unblock a previously blocked proxy.

        Args:
            proxy_id: The identifier of the proxy to unblock.
        """
        await self.redis.delete(f"{self.proxy_block_key}{proxy_id}")
        logger.bind(proxy_id=proxy_id).info("Proxy unblocked")

    async def get_all(self) -> list[ProxyModel]:
        """Retrieve all proxies from storage.

        Returns:
            List of all ProxyModel instances.
        """
        keys = await self.redis.keys(f"{self.proxy_key}*")

        keys = [
            k
            for k in keys
            if not k.startswith(self.proxy_block_key.encode())
            and not k == self.proxy_sorted_key.encode()
            and not k.endswith(b":sorted")
        ]

        proxies = []
        for key in keys:
            data = await self.redis.get(key)
            if data:
                proxies.append(ProxyModel.model_validate_json(data))

        logger.bind(count=len(proxies)).info("Retrieved all proxies")
        return proxies

    async def get_all_with_status(self) -> list[dict]:
        """Retrieve all proxies with their blocked status.

        Returns:
            List of dicts with proxy data and is_blocked status.
        """
        proxies = await self.get_all()
        result = []
        for proxy in proxies:
            is_blocked = await self.is_blocked(proxy.identifier)
            result.append(
                {
                    "proxy": proxy,
                    "is_blocked": is_blocked,
                }
            )
        return result

    async def validate_proxy(self, proxy: str) -> bool:
        """Validate a proxy by attempting to make a request through it.

        Args:
            proxy: The proxy string in httpx format.

        Returns:
            True if the proxy is valid, False otherwise.
        """
        timeout = self.cfg.timeouts.connection_timeout
        max_retries = self.cfg.retries.max_retries
        retry_delay = self.cfg.retries.retry_delay
        backoff_factor = self.cfg.network.backoff_factor

        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(
                    proxy=proxy, timeout=timeout
                ) as client:
                    response = await client.get(
                        self.cfg.parsing.proxy_validation_url
                    )
                    if 200 <= response.status_code < 300:
                        logger.bind(proxy=proxy).info(
                            "Proxy validated successfully"
                        )
                        return True
            except Exception as exc:
                logger.bind(
                    error_message=str(exc), proxy=proxy, attempt=attempt + 1
                ).warning(f"Proxy validation failed: {exc}")

            if attempt < max_retries - 1:
                delay = retry_delay * (backoff_factor**attempt)
                await asyncio.sleep(delay)

        logger.bind(proxy=proxy, max_retries=max_retries).error(
            "Proxy validation failed after all retries"
        )
        return False

    async def delete_proxy(self, proxy_id: str) -> None:
        """Delete a proxy from storage.

        Args:
            proxy_id: The identifier of the proxy to delete.
        """
        await self.redis.delete(f"{self.proxy_key}{proxy_id}")
        await self.redis.zrem(self.proxy_sorted_key, proxy_id)
        await self.redis.delete(f"{self.proxy_block_key}{proxy_id}")
        logger.bind(proxy_id=proxy_id).info("Proxy deleted")

    async def validate_all_proxies(self) -> None:
        """Validate all proxies and update their status in Redis."""
        # Get all proxy IDs from the sorted set
        sorted_ids = await self.redis.zrange(self.proxy_sorted_key, 0, -1)

        # Get all blocked proxy keys
        blocked_keys = await self.redis.keys(f"{self.proxy_block_key}*")

        # Extract proxy IDs from blocked keys
        blocked_ids = [
            key[len(self.proxy_block_key) :] for key in blocked_keys
        ]

        # Combine and deduplicate
        all_ids = set(sorted_ids + blocked_ids)

        # Collect proxies and validation tasks
        validation_tasks = []
        for proxy_id in all_ids:
            proxy = await self.get_proxy(proxy_id)
            if not proxy:
                continue
            proxy_str = proxy.to_httpx_proxy()
            task = self.validate_proxy(proxy_str)
            validation_tasks.append((proxy_id, task))

        # Await all validation tasks concurrently
        results = await asyncio.gather(*[task for _, task in validation_tasks])

        # Process results
        for i, is_valid in enumerate(results):
            proxy_id = validation_tasks[i][0]
            if is_valid:
                # Remove block key if exists
                await self.redis.delete(f"{self.proxy_block_key}{proxy_id}")
                # Add back to sorted set with score 0 (least used)
                await self.redis.zadd(self.proxy_sorted_key, {proxy_id: 0})
                logger.bind(proxy_id=proxy_id).info(
                    "Proxy validated and added back to sorted set"
                )
            else:
                # Remove from sorted set (mark as inactive)
                await self.redis.zrem(self.proxy_sorted_key, proxy_id)
                logger.bind(proxy_id=proxy_id).warning(
                    "Proxy validation failed, removed from sorted set"
                )
