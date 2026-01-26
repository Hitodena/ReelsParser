from fastapi import APIRouter

from .instagram_account import account_router
from .instagram_parsing import parsing_router
from .proxy import proxy_router

api_router = APIRouter(prefix="/api")
api_router.include_router(account_router)
api_router.include_router(parsing_router)
api_router.include_router(proxy_router)
