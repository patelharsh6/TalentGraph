"""Shared (cross-process) Gemini quota limiter backed by Redis fixed windows (plan §3.1)."""

import asyncio
import time

from redis.asyncio import Redis

from talentgraph.config import Settings
from talentgraph.core.errors import LLMQuotaExceeded


class RateLimiter:
    def __init__(self, redis: Redis, *, rpm: int, rpd: int) -> None:
        self._redis = redis
        self._rpm = rpm
        self._rpd = rpd

    @classmethod
    def from_settings(cls, settings: Settings) -> "RateLimiter":
        return cls(
            Redis.from_url(settings.redis_url),
            rpm=settings.llm_rpm_limit,
            rpd=settings.llm_rpd_limit,
        )

    async def acquire(self, model: str, *, max_wait_s: float = 60.0) -> None:
        """Wait for a per-minute slot; raise LLMQuotaExceeded if today's quota is used up."""
        day_key = f"llm:rpd:{model}:{time.strftime('%Y%m%d', time.gmtime())}"
        deadline = time.monotonic() + max_wait_s
        while True:
            minute = int(time.time() // 60)
            minute_key = f"llm:rpm:{model}:{minute}"
            async with self._redis.pipeline(transaction=True) as pipe:
                pipe.incr(minute_key)
                pipe.expire(minute_key, 120)
                pipe.incr(day_key)
                pipe.expire(day_key, 2 * 86400)
                used_min, _, used_day, _ = await pipe.execute()
            if used_day > self._rpd:
                await self._redis.decr(day_key)
                raise LLMQuotaExceeded(f"Daily quota reached for {model}")
            if used_min <= self._rpm:
                return
            # Over the minute window: give the slot back and wait for the next window.
            await self._redis.decr(minute_key)
            await self._redis.decr(day_key)
            if time.monotonic() >= deadline:
                raise LLMQuotaExceeded(f"Per-minute quota wait exceeded for {model}")
            await asyncio.sleep(60 - time.time() % 60 + 0.05)
