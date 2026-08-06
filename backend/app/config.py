"""
Sententia.ai — Configuration
Loads all environment variables with type validation via pydantic-settings.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────────────────
    app_name: str = "Sententia.ai"
    app_version: str = "0.1.0"
    debug: bool = False

    # ── LLM Providers ────────────────────────────────────────────────
    openrouter_api_key: str = ""
    groq_api_key: str = ""

    # ── Embeddings ───────────────────────────────────────────────────
    jina_api_key: str = ""
    google_api_key: str = ""

    # ── Qdrant ───────────────────────────────────────────────────────
    qdrant_url: str = ""
    qdrant_api_key: str = ""

    # ── Supabase ─────────────────────────────────────────────────────
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    # JWT secret from Supabase → Project Settings → API → JWT Settings
    # Used by the backend to verify access tokens issued by Supabase Auth.
    supabase_jwt_secret: str = ""

    # ── CORS ─────────────────────────────────────────────────────────
    # Comma-separated list of allowed origins
    cors_origins: str = "http://localhost:3000,https://*.pages.dev"


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings singleton."""
    return Settings()
