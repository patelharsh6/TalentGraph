"""Liveness and readiness probes (unauthenticated)."""

import asyncio
from collections.abc import Awaitable, Callable

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from talentgraph import PIPELINE_VERSION, __version__

router = APIRouter(tags=["health"])


@router.get("/health", summary="Liveness probe")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__, "pipeline_version": PIPELINE_VERSION}


async def _check(fn: Callable[[], Awaitable[object]]) -> str:
    try:
        await asyncio.wait_for(fn(), timeout=2.0)
    except Exception as exc:
        return f"error: {type(exc).__name__}"
    return "ok"


@router.get("/ready", summary="Readiness probe (DB, Redis, Chroma)")
async def ready(request: Request) -> JSONResponse:
    state = request.app.state

    async def db() -> None:
        async with state.engine.connect() as conn:
            await conn.execute(text("SELECT 1"))

    async def redis() -> None:
        await state.redis.ping()

    async def chroma() -> None:
        await asyncio.to_thread(state.chroma_heartbeat)

    checks = {"db": await _check(db), "redis": await _check(redis), "chroma": await _check(chroma)}
    ok = all(v == "ok" for v in checks.values())
    return JSONResponse(
        {"status": "ok" if ok else "degraded", "checks": checks}, 200 if ok else 503
    )
