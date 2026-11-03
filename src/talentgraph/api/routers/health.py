"""Liveness and readiness probes (unauthenticated)."""

import asyncio

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from talentgraph import PIPELINE_VERSION, __version__
from talentgraph.db.session import is_db_available

router = APIRouter(tags=["health"])


@router.get("/health", summary="Liveness probe")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__, "pipeline_version": PIPELINE_VERSION}


@router.get("/ready", summary="Readiness probe (DB, Redis, Chroma)")
@router.get("/healthz", summary="Readiness probe (DB, Redis, Chroma)")
async def ready(request: Request) -> JSONResponse:
    state = request.app.state

    async def check_db() -> str:
        if getattr(state, "engine", None) is None or not is_db_available():
            return "offline (in-memory fallback)"
        try:
            async with asyncio.timeout(0.4):
                async with state.engine.connect() as conn:
                    await conn.execute(text("SELECT 1"))
            return "ok"
        except Exception as exc:
            return f"error: {type(exc).__name__}"

    async def check_redis() -> str:
        redis_client = getattr(state, "redis", None)
        if redis_client is None:
            return "offline (in-memory fallback)"
        try:
            async with asyncio.timeout(0.4):
                await redis_client.ping()
            return "ok"
        except Exception as exc:
            return f"error: {type(exc).__name__}"

    async def check_chroma() -> str:
        heartbeat_fn = getattr(state, "chroma_heartbeat", None)
        if heartbeat_fn is None:
            return "offline (numpy fallback)"
        try:
            async with asyncio.timeout(0.4):
                await asyncio.to_thread(heartbeat_fn)
            return "ok"
        except Exception as exc:
            return f"error: {type(exc).__name__}"

    db_stat, redis_stat, chroma_stat = await asyncio.gather(
        check_db(), check_redis(), check_chroma()
    )

    checks = {
        "db": db_stat,
        "redis": redis_stat,
        "chroma": chroma_stat,
    }
    ok = all(v == "ok" for v in checks.values())
    return JSONResponse(
        {"status": "ok" if ok else "degraded", "checks": checks},
        status_code=200 if ok else 503,
    )
