"""Application settings. The only place that reads environment variables (plan §12)."""

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
    llm_timeout_s: float = 20.0
    # Every attempt, failed or not, counts against the free-tier daily quota (20/day).
    llm_max_attempts: int = 3
    llm_max_concurrency: int = 4
    llm_stub_latency_ms: int = 2500
    # Gemini "thinking" adds latency and isn't needed for extraction: low | medium | high
    # Blank leaves the model's default.
    llm_thinking_level: str = "low"

    # Embeddings
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # API
    api_key: SecretStr | None = None
    web_origin: str = "http://localhost:3000"
    rate_limit_per_min: int = 60
    max_upload_mb: int = 10
    max_pdf_pages: int = 20
    max_batch_files: int = 20

    # Uploads
    retain_uploads: bool = False
    upload_dir: str = "uploads"

    # Parsing
    parse_cache_ttl_s: int = 7 * 24 * 3600

    # Paths (relative to the working directory: the repo root, or /app in the container)
    fixtures_dir: str = Field(default="tests/fixtures/llm")
    config_dir: str = "config"
    taxonomy_dir: str = "data/taxonomy"

    @field_validator("gemini_api_key", "api_key", mode="before")
    @classmethod
    def _blank_key_is_none(cls, value: object) -> object:
        """A blank key (`GEMINI_API_KEY=`, `API_KEY=` in .env.example) means "no key", not empty."""
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("llm_model", mode="before")
    @classmethod
    def _validate_llm_model(cls, value: object) -> str:
        """Allow configuring any valid Gemini model name; defaults to gemini-3.8-flash."""
        if isinstance(value, str) and value.strip():
            return value.strip()
        return "gemini-3.8-flash"

    @property
    def llm_effective_mode(self) -> Literal["real", "fake", "stub"]:
        """`real` silently degrades to `fake` when no API key is configured."""
        if self.llm_mode == "real" and self.gemini_api_key is None:
            return "fake"
        return self.llm_mode


_settings_instance: Settings | None = None


def clear_settings_cache() -> None:
    global _settings_instance
    _settings_instance = None


def get_settings() -> Settings:
    global _settings_instance
    if _settings_instance is not None:
        return _settings_instance

    import sys
    from pathlib import Path

    from pydantic import ValidationError

    env_path = Path(".env")
    if not env_path.exists():
        import structlog

        structlog.get_logger(__name__).info(
            "config.env_missing",
            detail="No .env file found; using default dev configuration with in-memory fallbacks.",
        )

    try:
        _settings_instance = Settings()
        return _settings_instance
    except ValidationError as exc:
        print("\n" + "=" * 65, file=sys.stderr)
        print("[!] TalentGraph Configuration Error (.env):", file=sys.stderr)
        for err in exc.errors():
            field = " -> ".join(str(loc) for loc in err["loc"])
            msg = err["msg"]
            print(f"   * {field}: {msg}", file=sys.stderr)
        print(
            "\nPlease check your environment variables or restore .env from .env.example:",
            file=sys.stderr,
        )
        print("   Copy-Item .env.example .env (Windows PowerShell)", file=sys.stderr)
        print("   cp .env.example .env (Linux/macOS)", file=sys.stderr)
        print("=" * 65 + "\n", file=sys.stderr)
        sys.exit(1)


get_settings.cache_clear = clear_settings_cache  # type: ignore[attr-defined]
