"""Application settings, loaded from the environment / `.env`."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent
DATA_DIR = BACKEND_DIR / "data"


class Settings(BaseSettings):
    """Runtime configuration.

    Every machine-specific value comes from the environment; nothing secret is
    compiled into the app or shipped to the browser.
    """

    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    app_name: str = "SupportPilot AI"
    app_version: str = "1.0.0"
    app_env: str = "demo"
    database_url: str = Field(
        default="sqlite:///./data/supportpilot.db",
        validation_alias=AliasChoices("DATABASE_URL", "database_url"),
    )
    seed_on_startup: bool = True
    demo_reset_enabled: bool = True
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # --- LLM provider (OpenAI-compatible) ---
    llm_enabled: bool = True
    llm_provider: str = "OpenRouter"
    llm_base_url: str = Field(
        default="https://openrouter.ai/api/v1",
        validation_alias=AliasChoices("LLM_BASE_URL", "OPENROUTER_BASE_URL", "llm_base_url"),
    )
    llm_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("LLM_API_KEY", "OPENROUTER_API_KEY", "llm_api_key"),
    )
    llm_model: str = Field(
        default="nvidia/nemotron-3-super-120b-a12b:free",
        validation_alias=AliasChoices("LLM_MODEL", "OPENROUTER_MODEL", "llm_model"),
    )
    llm_timeout_seconds: float = 45.0
    llm_temperature: float = 0.2
    llm_max_tokens: int = 1400

    retrieval_top_k: int = 3

    @property
    def resolved_database_url(self) -> str:
        """Resolve relative SQLite paths against the backend directory."""
        url = self.database_url
        prefix = "sqlite:///"
        if not url.startswith(prefix):
            return url
        raw_path = url[len(prefix) :]
        path = Path(raw_path)
        if not path.is_absolute():
            path = BACKEND_DIR / path
        path.parent.mkdir(parents=True, exist_ok=True)
        return f"{prefix}{path.as_posix()}"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def llm_configured(self) -> bool:
        return bool(self.llm_api_key.strip())

    @property
    def ai_mode(self) -> str:
        return "llm" if (self.llm_enabled and self.llm_configured) else "fallback"


@lru_cache
def get_settings() -> Settings:
    return Settings()