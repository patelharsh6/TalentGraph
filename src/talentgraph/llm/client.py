"""Gemini LLM wrapper. Every LLM call in the system goes through here (plan §3.1)."""

import asyncio
import time
from typing import Protocol, TypeVar

import structlog
from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from pydantic import BaseModel, ValidationError
from tenacity import (
    AsyncRetrying,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential_jitter,
)

from talentgraph.config import Settings, get_settings
from talentgraph.core.errors import LLMError, LLMQuotaExceeded

T = TypeVar("T", bound=BaseModel)
log = structlog.get_logger(__name__)


class LLMClient(Protocol):
    async def extract(self, schema: type[T], system: str, user: str) -> T:
        """Return `schema` populated from the model's structured JSON output."""
        ...


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, genai_errors.APIError):
        return exc.code == 429 or exc.code >= 500
    return isinstance(exc, (TimeoutError, ConnectionError, LLMError))


class GeminiLLM:
    """Structured extraction on the Gemini API with a timeout, retries and a concurrency cap.

    A 429 that survives the retries raises `LLMQuotaExceeded`; agents then degrade to rules-only
    output (`status="partial"`).
    """

    def __init__(self, settings: Settings) -> None:
        if settings.gemini_api_key is None:
            raise LLMError("GEMINI_API_KEY is not configured")
        self._settings = settings
        self._client = genai.Client(api_key=settings.gemini_api_key.get_secret_value())
        self._semaphore = asyncio.Semaphore(settings.llm_max_concurrency)

    async def extract(self, schema: type[T], system: str, user: str) -> T:
        model = self._settings.llm_model
        try:
            return await self._extract_with_retries(model, schema, system, user)
        except genai_errors.APIError as exc:
            if exc.code == 429:
                log.warning("llm.quota_exceeded", model=model)
                raise LLMQuotaExceeded(f"Gemini quota exceeded for {model}") from exc
            raise LLMError(str(exc)) from exc

    async def _extract_with_retries(self, model: str, schema: type[T], system: str, user: str) -> T:
        retrying = AsyncRetrying(
            retry=retry_if_exception(_is_retryable),
            stop=stop_after_attempt(3),
            wait=wait_exponential_jitter(initial=1, max=8),
            reraise=True,
        )
        async for attempt in retrying:
            with attempt:
                return await self._call(model, schema, system, user)
        raise AssertionError("unreachable")

    async def _call(self, model: str, schema: type[T], system: str, user: str) -> T:
        level = self._settings.llm_thinking_level.strip().upper()
        config = types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
            response_json_schema=schema.model_json_schema(),
            temperature=0,
            thinking_config=types.ThinkingConfig(thinking_level=types.ThinkingLevel(level))
            if level
            else None,
        )
        start = time.perf_counter()
        async with self._semaphore, asyncio.timeout(self._settings.llm_timeout_s):
            response = await self._client.aio.models.generate_content(
                model=model, contents=user, config=config
            )
        usage = response.usage_metadata
        log.info(
            "llm.call",
            model=model,
            latency_ms=int((time.perf_counter() - start) * 1000),
            prompt_tokens=usage.prompt_token_count if usage else None,
            output_tokens=usage.candidates_token_count if usage else None,
        )
        if not response.text:
            raise LLMError("Empty response from Gemini")
        try:
            return schema.model_validate_json(response.text)
        except ValidationError as exc:
            raise LLMError(f"Response did not match {schema.__name__}: {exc}") from exc


def get_llm(settings: Settings | None = None) -> LLMClient:
    """Pick the client for `LLM_MODE`; `real` without an API key falls back to FakeLLM."""
    from talentgraph.llm.fake import FakeLLM

    settings = settings or get_settings()
    mode = settings.llm_effective_mode
    if mode == "real":
        return GeminiLLM(settings)
    latency = settings.llm_stub_latency_ms if mode == "stub" else 0
    return FakeLLM(settings.fixtures_dir, latency_ms=latency)
