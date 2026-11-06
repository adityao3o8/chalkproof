"""App settings loaded from environment / .env."""

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str = ""
    anthropic_api_key: str = ""
    google_api_key: str = ""

    generator_model: str = "openai:gpt-4o-mini"
    qc_model: str = "anthropic:claude-3-5-haiku-latest"

    llm_timeout_seconds: int = 90
    llm_max_retries: int = 2

    tavily_api_key: str = ""
    youtube_api_key: str = ""
    google_books_api_key: str = ""

    database_url: str = "sqlite:///./chalkproof.db"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # When true (or when no LLM keys are set), generation uses a local fixture lesson.
    chalkproof_demo_mode: bool = False

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
