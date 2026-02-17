from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.services import (
    BrowserManager,
    DatabaseSessionManager,
    InstagramOrchestrator,
    ProxyManager,
    RobokassaService,
)


def get_db(request: Request) -> DatabaseSessionManager:
    """Get database manager from app state"""
    return request.app.state.db


def get_orchestrator(request: Request) -> InstagramOrchestrator:
    """Get Instagram orchestrator from app state"""
    return request.app.state.parser_orchestrator


def get_browser(request: Request) -> BrowserManager:
    """Get browser manager from app state"""
    return request.app.state.browser


def get_proxy_manager(request: Request) -> ProxyManager:
    """Get proxy manager from app state"""
    return request.app.state.proxy_manager


def get_parser_orchestrator(request: Request) -> InstagramOrchestrator:
    """Get parser orchestrator from app state"""
    return request.app.state.parser_orchestrator


def get_robokassa() -> RobokassaService:
    """Get Robokassa service"""
    return RobokassaService()


@asynccontextmanager
async def get_session(
    request: Request,
) -> AsyncGenerator[AsyncSession, None]:
    """
    Get database session as context manager.

    Usage:
        async with get_session(request) as session:
            # use session
    """
    db = get_db(request)
    async with db.session() as session:
        yield session
