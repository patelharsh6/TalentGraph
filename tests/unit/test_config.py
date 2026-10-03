from pydantic import SecretStr

from talentgraph.config import Settings


def test_real_mode_without_key_degrades_to_fake() -> None:
    s = Settings(_env_file=None, llm_mode="real", gemini_api_key=None)
    assert s.llm_effective_mode == "fake"


def test_real_mode_with_key_stays_real() -> None:
    s = Settings(_env_file=None, llm_mode="real", gemini_api_key=SecretStr("x"))
    assert s.llm_effective_mode == "real"


def test_defaults_use_gemini_free_tier_models() -> None:
    s = Settings(_env_file=None)
    assert s.llm_model.startswith("gemini-")
    assert s.llm_fallback_model is not None
