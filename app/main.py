from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.core import load
from app.services import (
    BrowserManager,
    DatabaseSessionManager,
    InstagramOrchestrator,
    ProxyManager,
    RedisManager,
)

config = load()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    app.state.db = DatabaseSessionManager(config.environment.get_db_url())
    app.state.redis = RedisManager(config.environment.redis_url)

    await app.state.redis.connect()
    app.state.db.init()

    # Proxy manager
    if not app.state.redis.redis:
        raise RuntimeError("Redis is not initialized")
    app.state.proxy_manager = ProxyManager(app.state.redis.redis, config)

    # Browser manager
    app.state.browser = BrowserManager(config)
    await app.state.browser.start()

    # Orchestrator
    app.state.parser_orchestrator = InstagramOrchestrator(
        config=config, proxy_manager=app.state.proxy_manager
    )

    yield

    # Shutdown
    await app.state.redis.close()
    await app.state.db.close()
    await app.state.browser.close()


app = FastAPI(title="Instagram Reels Parser", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.environment.cors_allow_origins,
    allow_credentials=config.environment.cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/", tags=["root"])
async def root():
    return {
        "message": "Instagram Reels Parser",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", tags=["root"])
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="localhost",
        port=8000,
        reload=False,
        log_level=config.environment.log_level.lower(),
    )
