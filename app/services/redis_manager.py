from loguru import logger
from redis.asyncio import Redis


class RedisManager:
    def __init__(self, url: str):
        self.redis: Redis | None = None
        self.url = url

    async def connect(self):
        self.redis = await Redis.from_url(
            self.url, encoding="utf-8", decode_responses=True
        )
        logger.bind(url=self.url).info("Connected to the redis successfully")

    async def close(self):
        if self.redis:
            await self.redis.close()
            logger.bind(url=self.url).info(
                "Connection to the redis closed successfuly"
            )
