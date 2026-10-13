"""Application settings. The only place that reads environment variables (plan §12)."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    app_env: Literal["dev", "test", "prod"] = "dev"
    log_level: str = "INFO"

    # Storage
    database_url: str = "postgresql+asyncpg://talentgraph:talentgraph@localhost:5432/talentgraph"
    redis_url: str = "redis://localhost:6379/0"
    chroma_host: str = "localhost"
    chroma_port: int = 8000

    # LLM (Gemini)
    gemini_api_key: SecretStr | None = None
    llm_mode: Literal["real", "fake", "stub"] = "real"
    llm_model: str = "gemini-3.8-flash"
    llm_timeout_s: float = 8.0
    llm_max_concurrency: int = 4
    llm_stub_latency_ms: int = 2500

    # Embeddings
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # API
    api_key: SecretStr | None = None
    rate_limit_per_min: int = 60
    max_upload_mb: int = 10
    max_batch_files: int = 20

    # Uploads
    retain_uploads: bool = False
    upload_dir: str = "uploads"

    # Paths
    fixtures_dir: str = Field(default="tests/fixtures/llm")

    @field_validator("gemini_api_key", "api_key", mode="before")
    @classmethod
    def _blank_key_is_none(cls, value: object) -> object:
        """A blank key (`GEMINI_API_KEY=`, `API_KEY=` in .env.example) means "no key", not empty."""
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @property
    def llm_effective_mode(self) -> Literal["real", "fake", "stub"]:
        """`real` silently degrades to `fake` when no API key is configured."""
        if self.llm_mode == "real" and self.gemini_api_key is None:
            return "fake"
        return self.llm_mode


@lru_cache
def get_settings() -> Settings:
    return Settings()
