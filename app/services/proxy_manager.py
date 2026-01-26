import asyncio
from datetime import datetime, timedelta, timezone

import httpx
from loguru import logger
from redis.asyncio import Redis

from app.core import Config
from app.models import ProxyModel


class ProxyManager:
    """Manages proxy operations including validation, blocking, and retrieval."""

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

    async def add_proxy(self, proxy: ProxyModel) -> ProxyModel | None:
        """Add a new proxy after validating it.

        Args:
            proxy: ProxyModel instance to add.

        Returns:
            Proxy Model if added successfully, None if validation failed.
        """
        proxy_str = proxy.to_httpx_proxy()
        is_valid = await self.validate_proxy(proxy_str)
        if not is_valid:
            logger.bind(proxy_id=proxy.identifier).warning(
                "Proxy validation failed, not adding"
            )
            return None

        key = f"{self.proxy_key}{proxy.identifier}"

        await self.redis.set(key, proxy.model_dump_json())

        await self.redis.zadd(self.proxy_sorted_key, {proxy.identifier: 0})

        logger.bind(proxy_id=proxy.identifier).info("Proxy added successfully")
        return proxy

    async def get_proxy(self, proxy_id: str) -> ProxyModel | None:
        """Retrieve a proxy by its identifier.

        Args:
            proxy_id: The unique identifier of the proxy.

        Returns:
            ProxyModel instance if found, None otherwise.
        """
        key = f"f{self.proxy_key}:{proxy_id}"
        data = await self.redis.get(key)

        if not data:
            logger.bind(proxy_id=proxy_id).warning("Proxy not found")
            return None

        logger.bind(proxy_id=proxy_id).info("Proxy retrieved successfully")
        return ProxyModel.model_validate_json(data)

    async def get_least_used(self) -> ProxyModel | None:
        """Get the least used active and unblocked proxy.

        Returns:
            The least used ProxyModel if available, None otherwise.
        """
        results = await self.redis.zrange(self.proxy_sorted_key, 0, 0)

        if not results:
            logger.warning("No proxies available")
            return None

        proxy_id = results[0]
        proxy = await self.get_proxy(proxy_id)

        if proxy and proxy.is_active and not proxy.is_blocked:
            logger.bind(proxy_id=proxy_id).info("Least used proxy selected")
            return proxy

        await self.redis.zrem("proxy:sorted", proxy_id)
        return await self.get_least_used()

    async def mark_used(self, proxy_id: str):
        """Mark a proxy as used, updating its last used time and request count.

        Args:
            proxy_id: The identifier of the proxy to mark as used.
        """
        proxy = await self.get_proxy(proxy_id)

        if not proxy:
            return None

        proxy.last_used = datetime.now(timezone.utc)
        proxy.request_count += 1

        await self.redis.set(
            f"{self.proxy_key}{proxy_id}", proxy.model_dump_json()
        )

        await self.redis.zadd(
            self.proxy_sorted_key, {proxy_id: proxy.last_used.timestamp()}
        )
        logger.bind(proxy_id=proxy_id, request_count=proxy.request_count).info(
            "Proxy marked as used"
        )

    async def block_proxy(self, proxy_id: str, minutes: int = 60):
        """Block a proxy for a specified number of minutes.

        Args:
            proxy_id: The identifier of the proxy to block.
            minutes: Number of minutes to block the proxy (default 60).
        """
        proxy = await self.get_proxy(proxy_id)
        if not proxy:
            return None

        proxy.is_blocked = True

        await self.redis.set(
            f"{self.proxy_key}{proxy_id}", proxy.model_dump_json()
        )

        block_key = f"{self.proxy_block_key}{proxy_id}"
        await self.redis.setex(block_key, timedelta(minutes=minutes), "1")
        logger.bind(proxy_id=proxy_id, minutes=minutes).info("Proxy blocked")

    async def unblock_proxy(self, proxy_id: str):
        """Unblock a previously blocked proxy.

        Args:
            proxy_id: The identifier of the proxy to unblock.
        """
        proxy = await self.get_proxy(proxy_id)

        if not proxy:
            return

        proxy.is_blocked = False

        await self.redis.set(
            f"{self.proxy_key}{proxy_id}", proxy.model_dump_json()
        )

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
            if not k.startswith(f"{self.proxy_block_key}")
            and not k.startswith(f"{self.proxy_sorted_key}")
        ]

        proxies = []
        for key in keys:
            data = await self.redis.get(key)
            if data:
                proxies.append(ProxyModel.model_validate_json(data))

        logger.bind(count=len(proxies)).info("Retrieved all proxies")
        return proxies

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
                    error_message=exc, proxy=proxy, attempt=attempt + 1
                ).warning(f"Proxy validation failed: {exc}")

            if attempt < max_retries - 1:
                delay = retry_delay * (backoff_factor**attempt)
                await asyncio.sleep(delay)

        logger.bind(proxy=proxy, max_retries=max_retries).error(
            "Proxy validation failed after all retries"
        )
        return False

    async def delete_proxy(self, proxy_id: str):
        """Delete a proxy from storage.

        Args:
            proxy_id: The identifier of the proxy to delete.
        """
        await self.redis.delete(f"{self.proxy_key}{proxy_id}")
        await self.redis.zrem(self.proxy_sorted_key, proxy_id)
        await self.redis.delete(f"{self.proxy_block_key}{proxy_id}")
        logger.bind(proxy_id=proxy_id).info("Proxy deleted")

    async def validate_all_proxies(self):
        """Validate all proxies and unblock those that are now valid."""
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
            validation_tasks.append((proxy_id, proxy, task))

        # Await all validation tasks concurrently
        results = await asyncio.gather(
            *[task for _, _, task in validation_tasks]
        )

        # Process results
        for i, is_valid in enumerate(results):
            proxy_id, proxy, _ = validation_tasks[i]
            if is_valid and proxy.is_blocked:
                # Unblock the proxy
                proxy.is_blocked = False
                await self.redis.set(
                    f"{self.proxy_key}{proxy_id}", proxy.model_dump_json()
                )
                await self.redis.delete(f"{self.proxy_block_key}{proxy_id}")
                # Add back to sorted set with score 0 (least used)
                await self.redis.zadd(self.proxy_sorted_key, {proxy_id: 0})
                logger.bind(proxy_id=proxy_id).info(
                    "Proxy unblocked and added back to sorted set"
                )
