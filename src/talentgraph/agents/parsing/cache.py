"""Step 2.12: parse cache keyed by `sha256(file)` + `PIPELINE_VERSION` (plan §4.4).

Only complete (`status="ok"`) results are cached, so a resume parsed while the LLM was down is
parsed again, with the LLM, on the next upload. A cache outage never fails a parse.
"""

from typing import Protocol

import structlog
from redis.asyncio import Redis
from redis.exceptions import RedisError

from talentgraph import PIPELINE_VERSION
from talentgraph.core.schemas.resume import ParseResult

log = structlog.get_logger(__name__)


def cache_key(sha256: str) -> str:
    return f"parse:{sha256}:{PIPELINE_VERSION}"


class ParseCache(Protocol):
    async def get(self, sha256: str) -> ParseResult | None: ...

    async def set(self, sha256: str, result: ParseResult) -> None: ...


class InMemoryParseCache:
    """Process-local cache for tests and for running without Redis."""

    def __init__(self) -> None:
        self._data: dict[str, str] = {}

    async def get(self, sha256: str) -> ParseResult | None:
        raw = self._data.get(cache_key(sha256))
        return ParseResult.model_validate_json(raw) if raw else None

    async def set(self, sha256: str, result: ParseResult) -> None:
        self._data[cache_key(sha256)] = result.model_dump_json()


class RedisParseCache:
    def __init__(self, redis: "Redis", *, ttl_s: int) -> None:
        self._redis = redis
        self._ttl_s = ttl_s

    @classmethod
    def from_url(cls, url: str, *, ttl_s: int) -> "RedisParseCache":
        return cls(Redis.from_url(url), ttl_s=ttl_s)

    async def get(self, sha256: str) -> ParseResult | None:
        try:
            raw = await self._redis.get(cache_key(sha256))
        except (RedisError, OSError) as exc:
            log.warning("parse_cache.get_failed", error=str(exc))
            return None
        return ParseResult.model_validate_json(raw) if raw else None

    async def set(self, sha256: str, result: ParseResult) -> None:
        try:
            await self._redis.set(cache_key(sha256), result.model_dump_json(), ex=self._ttl_s)
        except (RedisError, OSError) as exc:
            log.warning("parse_cache.set_failed", error=str(exc))

    async def aclose(self) -> None:
        await self._redis.aclose()
