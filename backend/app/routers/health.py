"""Liveness endpoint used by Docker/HF healthchecks."""
from __future__ import annotations

from fastapi import APIRouter

from app.config import get_settings

router = APIRouter()


@router.get("/health")
def health() -> dict:
    # Always 200 if the process is up; reports config without calling OpenRouter.
    return {
        "status": "ok",
        "openrouter_key_configured": bool(get_settings().openrouter_api_key),
    }
