"""
Sententia.ai — Configuration
Loads all environment variables with type validation via pydantic-settings.
"""

from functools import lru_cache
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import os


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
    simulation_mode: str = "auto"  # "true" | "false" | "auto"


    # ── LLM Providers ────────────────────────────────────────────────
    openrouter_api_key: str = ""
    groq_api_key: str = ""

    # ── Embeddings ───────────────────────────────────────────────────
    jina_api_key: str = ""
    google_api_key: str = ""

    # ── Qdrant ───────────────────────────────────────────────────────
    qdrant_url: str = ""
    qdrant_api_key: str = ""

    # ── Supabase ─────────────────────────────────────────────────────────
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_jwt_secret: str = ""

    @model_validator(mode="after")
    def _resolve_aliases(self) -> "Settings":
        """
        Accept common alternate env var names so Render / HF Spaces / local .env
        all work without renaming variables.

        Render convention:  SUPABASE_SERVICE_KEY  (shorter)
        Our internal name:  SUPABASE_SERVICE_ROLE_KEY
        """
        # SUPABASE_SERVICE_KEY  →  supabase_service_role_key
        if not self.supabase_service_role_key:
            self.supabase_service_role_key = os.environ.get("SUPABASE_SERVICE_KEY", "")

        # SUPABASE_ANON_KEY  →  supabase_anon_key
        if not self.supabase_anon_key:
            self.supabase_anon_key = os.environ.get("SUPABASE_ANON_KEY", "")

        # SUPABASE_JWT_SECRET already matched by name
        return self

    # ── CORS ─────────────────────────────────────────────────────────
    # Comma-separated list of allowed origins
    cors_origins: str = "http://localhost:3000,https://*.pages.dev"


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings singleton."""
    return Settings()
