import contextlib
import time
from typing import AsyncIterator

from loguru import logger
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


class DatabaseSessionManager:
    def __init__(self, url: str) -> None:
        self._engine: AsyncEngine | None = None
        self._sessionmaker: async_sessionmaker[AsyncSession] | None = None
        self.url = url

    def init(self) -> None:
        logger.bind(url=self.url).info("Connecting to DB...")
        self._engine = create_async_engine(
            url=self.url,
            pool_pre_ping=True,
        )
        self._sessionmaker = async_sessionmaker(
            bind=self._engine,
            expire_on_commit=False,
            autoflush=False,
        )
        logger.bind(url=self.url).info("Successfully connected to DB")

    async def close(self) -> None:
        logger.bind(url=self.url).info("Closing DB connection...")
        if self._engine is None:
            logger.bind(url=self.url).critical("DB engine is not started")
            raise RuntimeError("DB engine is not started. Start by .init()")
        await self._engine.dispose()
        self._engine = None
        self._sessionmaker = None
        logger.bind(url=self.url).info(
            "DB connection was successfully closed"
        )

    @contextlib.asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        if self._sessionmaker is None:
            logger.critical("DatabaseSessionManager is not initialized")
            raise RuntimeError("DatabaseSessionManager is not initialized")
        async with self._sessionmaker() as session:
            try:
                start_time = time.perf_counter()
                logger.info("Yielding session")
                yield session
                elapsed_time = time.perf_counter() - start_time
                logger.bind(execution_time=f"{elapsed_time:.2f}").info(
                    "Session yielded successfully"
                )
            except Exception:
                logger.exception("Failed to yield session")
                await session.rollback()
                raise
            finally:
                await session.close()

    @contextlib.asynccontextmanager
    async def connect(self) -> AsyncIterator[AsyncConnection]:
        if self._engine is None:
            logger.critical("DatabaseSessionManager is not initialized")
            raise RuntimeError("DatabaseSessionManager is not initialized")
        async with self._engine.begin() as connection:
            try:
                start_time = time.perf_counter()
                logger.info("Yielding connection")
                yield connection
                elapsed_time = time.perf_counter() - start_time
                logger.bind(execution_time=f"{elapsed_time:.2f}").info(
                    "Connection yielded successfully"
                )
            except Exception:
                logger.exception("Failed to yield connection")
                await connection.rollback()
                raise
            finally:
                await connection.close()
