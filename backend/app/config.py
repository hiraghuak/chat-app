"""Application configuration, loaded from environment / .env."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo root: backend/app/config.py -> parents[2]
ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # OpenRouter (OpenAI-compatible). Key is optional at import time so the app
    # (and /health) still boots without it; it is validated per-request instead.
    openrouter_api_key: str | None = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    # OpenRouter's auto-router over currently-available free models. Robust to
    # the free catalog rotating and to individual models being saturated —
    # override with a specific ":free" model id if you prefer.
    openrouter_model: str = "openrouter/free"

    # Embeddings (local ONNX via fastembed, no API cost).
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_cache_dir: str = str(ROOT / ".fastembed_cache")

    # Retrieval / data.
    data_dir: str = str(ROOT / "data")
    top_k: int = 5
    min_score: float = 0.15          # below this, treat query as out-of-scope

    # Networking / limits.
    request_timeout_seconds: float = 60.0
    allowed_origins: str = "http://localhost:5173,http://localhost:3000,http://localhost:7860"
    rate_limit_per_minute: int = 15
    rate_limit_per_day: int = 200

    # Optional attribution headers OpenRouter shows on its dashboard.
    app_url: str = "https://huggingface.co/spaces"
    app_title: str = "DarGlobal + Wasalt Real Estate Chatbot"

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
