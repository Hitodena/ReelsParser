from fastapi import Request

from app.services import (
    BrowserManager,
    DatabaseSessionManager,
    InstagramOrchestrator,
    ProxyManager,
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
