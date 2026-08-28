"""FastAPI app: serves the grounded chat API and the built React UI."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import ROOT, get_settings
from app.ratelimit import RateLimiter
from app.rag import RagEngine
from app.routers import chat, health

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("chatapp")

FRONTEND_DIST = ROOT / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info("Loading RAG engine (model=%s)…", settings.embedding_model)
    app.state.rag = RagEngine(settings)
    app.state.rate_limiter = RateLimiter(
        settings.rate_limit_per_minute, settings.rate_limit_per_day
    )
    logger.info(
        "Ready: %d listings indexed; OpenRouter key configured=%s",
        len(app.state.rag.listings), bool(settings.openrouter_api_key),
    )
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="DarGlobal + Wasalt Real Estate Chatbot", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=False,
    )

    app.include_router(health.router)
    app.include_router(chat.router, prefix="/api")

    # Serve the built SPA (present in the container / after `npm run build`).
    if FRONTEND_DIST.is_dir():
        app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="static")
    else:
        @app.get("/")
        def root() -> dict:
            return {"status": "backend running", "note": "frontend build not found"}

    return app


app = create_app()
