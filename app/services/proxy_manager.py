from datetime import datetime, timedelta, timezone

from loguru import logger
from redis.asyncio import Redis

from app.models import ProxyModel


class ProxyManager:
    def __init__(self, redis: Redis) -> None:
        self.redis = redis
        self.proxy_key = "proxy:"
        self.proxy_sorted_key = f"{self.proxy_key}sorted"
        self.proxy_block_key = f"{self.proxy_key}blocked:"
        logger.info("ProxyManager initialized")

    async def add_proxy(self, proxy: ProxyModel) -> str:
        key = f"{self.proxy_key}{proxy.identifier}"

        await self.redis.set(key, proxy.model_dump_json())

        await self.redis.zadd(self.proxy_sorted_key, {proxy.identifier: 0})

        logger.bind(proxy_id=proxy.identifier).info("Proxy added successfully")
        return proxy.identifier

    async def get_proxy(self, proxy_id: str) -> ProxyModel | None:
        key = f"f{self.proxy_key}:{proxy_id}"
        data = await self.redis.get(key)

        if not data:
            logger.bind(proxy_id=proxy_id).warning("Proxy not found")
            return None

        logger.bind(proxy_id=proxy_id).info("Proxy retrieved successfully")
        return ProxyModel.model_validate_json(data)

    async def get_least_used(self) -> ProxyModel | None:
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

    async def delete_proxy(self, proxy_id: str):
        await self.redis.delete(f"{self.proxy_key}{proxy_id}")
        await self.redis.zrem(self.proxy_sorted_key, proxy_id)
        await self.redis.delete(f"{self.proxy_block_key}{proxy_id}")
        logger.bind(proxy_id=proxy_id).info("Proxy deleted")
