"""Application settings. The only place that reads environment variables (plan §12)."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
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

    # Celery
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"
    celery_concurrency: int = 4

    # LLM (Gemini)
    gemini_api_key: SecretStr | None = None
    llm_mode: Literal["real", "fake", "stub"] = "real"
    llm_model: str = "gemini-3.8-flash"
    llm_fallback_model: str | None = "gemini-3.5-flash-lite"
    llm_timeout_s: float = 8.0
    llm_max_concurrency: int = 4
    llm_rpm_limit: int = 10
    llm_rpd_limit: int = 250
    llm_stub_latency_ms: int = 2500

    # Embeddings
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # API limits
    max_upload_mb: int = 10
    max_batch_files: int = 100
    default_rate_limit_per_min: int = 60
    max_inflight_per_key: int = 50

    # Webhooks / uploads
    webhook_max_attempts: int = 5
    retain_uploads: bool = False
    upload_dir: str = "uploads"

    # Observability
    otel_enabled: bool = False
    otel_exporter_otlp_endpoint: str = "http://localhost:4317"

    # Paths
    fixtures_dir: str = Field(default="tests/fixtures/llm")

    @property
    def llm_effective_mode(self) -> Literal["real", "fake", "stub"]:
        """`real` silently degrades to `fake` when no API key is configured."""
        if self.llm_mode == "real" and self.gemini_api_key is None:
            return "fake"
        return self.llm_mode


@lru_cache
def get_settings() -> Settings:
    return Settings()
