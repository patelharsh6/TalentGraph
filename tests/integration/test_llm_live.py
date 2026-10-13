"""Exit criterion 0-G (optional half): one real Gemini `extract()` returns a valid Pydantic object.

Uses free-tier quota (one request) and only synthetic text. Skips when no key is configured:
    GEMINI_API_KEY=... uv run pytest -m llm
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from talentgraph.config import Settings, get_settings
from talentgraph.llm.client import GeminiLLM

pytestmark = pytest.mark.llm


class Contact(BaseModel):
    name: str
    email: str


async def test_real_extract_returns_valid_object() -> None:
    settings: Settings = get_settings()
    if settings.gemini_api_key is None:
        pytest.skip("GEMINI_API_KEY is not set")
    llm = GeminiLLM(settings, rate_limiter=None)  # no Redis needed for a single call
    result = await llm.extract(
        Contact,
        "Extract the person's name and email address.",
        "Contact: Jane Example, jane.example@example.com, +1 555 0100",
    )
    assert isinstance(result, Contact)
    assert result.email == "jane.example@example.com"
