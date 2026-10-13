from pathlib import Path

from pydantic import SecretStr

from talentgraph.config import Settings


def test_real_mode_without_key_degrades_to_fake() -> None:
    s = Settings(_env_file=None, llm_mode="real", gemini_api_key=None)
    assert s.llm_effective_mode == "fake"


def test_blank_key_from_env_file_degrades_to_fake(tmp_path: Path) -> None:
    """A .env copied from .env.example has `GEMINI_API_KEY=`; that must mean "no key"."""
    env = tmp_path / ".env"
    env.write_text("LLM_MODE=real\nGEMINI_API_KEY=\n", encoding="utf-8")
    s = Settings(_env_file=str(env))
    assert s.gemini_api_key is None
    assert s.llm_effective_mode == "fake"


def test_real_mode_with_key_stays_real() -> None:
    s = Settings(_env_file=None, llm_mode="real", gemini_api_key=SecretStr("x"))
    assert s.llm_effective_mode == "real"


def test_defaults_use_gemini_free_tier_model() -> None:
    s = Settings(_env_file=None)
    assert s.llm_model.startswith("gemini-")


def test_blank_api_key_means_no_key(tmp_path: Path) -> None:
    env = tmp_path / ".env"
    env.write_text("API_KEY=\n", encoding="utf-8")
    assert Settings(_env_file=str(env)).api_key is None
