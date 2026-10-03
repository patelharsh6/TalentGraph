import pytest

from talentgraph.config import Settings


@pytest.fixture
def settings(tmp_path: object) -> Settings:
    """Offline settings: no API key, fake LLM."""
    return Settings(
        _env_file=None, llm_mode="fake", gemini_api_key=None, fixtures_dir=str(tmp_path)
    )
