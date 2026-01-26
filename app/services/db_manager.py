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
        """Initialize the DatabaseSessionManager.

        Args:
            url (str): The database connection URL.
        """
        self._engine: AsyncEngine | None = None
        self._sessionmaker: async_sessionmaker[AsyncSession] | None = None
        self.url = url

    def init(self) -> None:
        """Initialize the database engine and sessionmaker.

        This method sets up the asynchronous database engine and sessionmaker
        using the provided URL.
        """
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
        """Close the database connection.

        This method disposes of the database engine and resets the internal state.

        Raises:
            RuntimeError: If the database engine is not started.
        """
        logger.bind(url=self.url).info("Closing DB connection...")
        if self._engine is None:
            logger.bind(url=self.url).critical("DB engine is not started")
            raise RuntimeError("DB engine is not started. Start by .init()")
        await self._engine.dispose()
        self._engine = None
        self._sessionmaker = None
        logger.bind(url=self.url).info("DB connection was successfully closed")

    @contextlib.asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        """Provide an asynchronous database session.

        This context manager yields an AsyncSession for database operations.
        It handles logging, rollback on exceptions, and session cleanup.

        Yields:
            AsyncSession: The database session.

        Raises:
            RuntimeError: If the DatabaseSessionManager is not initialized.
        """
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
        """Provide an asynchronous database connection.

        This context manager yields an AsyncConnection for database operations.
        It handles logging, rollback on exceptions, and connection cleanup.

        Yields:
            AsyncConnection: The database connection.

        Raises:
            RuntimeError: If the DatabaseSessionManager is not initialized.
        """
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
