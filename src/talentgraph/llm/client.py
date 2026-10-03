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
from talentgraph.llm.ratelimit import RateLimiter

T = TypeVar("T", bound=BaseModel)
log = structlog.get_logger(__name__)


class LLMClient(Protocol):
    async def extract(self, schema: type[T], system: str, user: str) -> T:
        """Return `schema` populated from the model's structured JSON output."""
        ...


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, genai_errors.APIError):
        return exc.code == 429 or exc.code >= 500
    return isinstance(exc, (TimeoutError, ConnectionError, LLMError)) and not isinstance(
        exc, LLMQuotaExceeded
    )


class GeminiLLM:
    """Structured extraction on the Gemini API with rate limiting, retries and model fallback."""

    def __init__(self, settings: Settings, rate_limiter: RateLimiter | None = None) -> None:
        if settings.gemini_api_key is None:
            raise LLMError("GEMINI_API_KEY is not configured")
        self._settings = settings
        self._client = genai.Client(api_key=settings.gemini_api_key.get_secret_value())
        self._semaphore = asyncio.Semaphore(settings.llm_max_concurrency)
        self._rate_limiter = rate_limiter

    async def extract(self, schema: type[T], system: str, user: str) -> T:
        models = [self._settings.llm_model]
        if self._settings.llm_fallback_model:
            models.append(self._settings.llm_fallback_model)

        last_exc: BaseException | None = None
        for model in models:
            try:
                return await self._extract_with_retries(model, schema, system, user)
            except (genai_errors.APIError, LLMQuotaExceeded) as exc:
                quota = isinstance(exc, LLMQuotaExceeded) or exc.code == 429
                if not quota:
                    raise LLMError(str(exc)) from exc
                log.warning("llm.quota_fallback", model=model)
                last_exc = exc
        raise LLMQuotaExceeded("All configured Gemini models are over quota") from last_exc

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
        if self._rate_limiter is not None:
            await self._rate_limiter.acquire(model)
        config = types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
            response_json_schema=schema.model_json_schema(),
            temperature=0,
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
        return GeminiLLM(settings, RateLimiter.from_settings(settings))
    latency = settings.llm_stub_latency_ms if mode == "stub" else 0
    return FakeLLM(settings.fixtures_dir, latency_ms=latency)
