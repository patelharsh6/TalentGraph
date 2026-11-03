"""FastAPI application. Run with `uvicorn talentgraph.api.main:app`."""

import asyncio
import contextlib
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager

import structlog
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis

from talentgraph import __version__
from talentgraph.agents.coach.agent import CoachAgent
from talentgraph.agents.matching.agent import MatchingAgent
from talentgraph.agents.matching.job_parser import JobParser
from talentgraph.agents.normalization.agent import NormalizationAgent
from talentgraph.agents.parsing.agent import ParsingAgent
from talentgraph.agents.parsing.cache import InMemoryParseCache, RedisParseCache
from talentgraph.agents.search.agent import SearchAgent
from talentgraph.api.problems import register_problem_handlers
from talentgraph.api.ratelimit import limiter
from talentgraph.api.routers import (
    batch,
    candidates,
    coach,
    health,
    jobs,
    match,
    parse,
    search,
    skills,
)
from talentgraph.api.routers import (
    eval as eval_router,
)
from talentgraph.config import get_settings
from talentgraph.core.net import is_service_reachable_async, parse_host_port
from talentgraph.db.repositories.taxonomy import get_taxonomy_repository
from talentgraph.db.session import (
    dispose_engine,
    init_engine,
    is_db_available,
    set_db_available,
)
from talentgraph.llm.client import get_llm
from talentgraph.observability.logging import configure_logging
from talentgraph.orchestrator.batch import recover_stale_batches

log = structlog.get_logger(__name__)


def _chroma_heartbeat_factory(host: str, port: int) -> Callable[[], int]:
    def heartbeat() -> int:
        import chromadb

        return int(chromadb.HttpClient(host=host, port=port).heartbeat())

    return heartbeat


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.log_level)

    # 1. Non-blocking service probe for Postgres, Redis, and Chroma concurrently (<250ms total)
    db_host, db_port = parse_host_port(settings.database_url, 5432)
    redis_host, redis_port = parse_host_port(settings.redis_url, 6379)
    chroma_host, chroma_port = settings.chroma_host, settings.chroma_port

    db_ok, redis_ok, chroma_ok = await asyncio.gather(
        is_service_reachable_async(db_host, db_port, timeout_s=0.25),
        is_service_reachable_async(redis_host, redis_port, timeout_s=0.25),
        is_service_reachable_async(chroma_host, chroma_port, timeout_s=0.25),
        return_exceptions=True,
    )

    # Initialize Postgres (or fallback to in-memory)
    if db_ok is True:
        try:
            app.state.engine = init_engine(settings.database_url)
            set_db_available(True)
            log.info("lifespan.db_connected", host=db_host, port=db_port)
        except Exception as exc:
            log.warning("lifespan.db_init_warning", error=str(exc))
            app.state.engine = None
            set_db_available(False)
    else:
        app.state.engine = None
        set_db_available(False)
        log.info("lifespan.db_offline_fallback", host=db_host, port=db_port)

    # Initialize Redis (or fallback to in-memory)
    if redis_ok is True:
        try:
            app.state.redis = Redis.from_url(settings.redis_url)
            log.info("lifespan.redis_connected", host=redis_host, port=redis_port)
        except Exception as exc:
            log.warning("lifespan.redis_init_warning", error=str(exc))
            app.state.redis = None
    else:
        app.state.redis = None
        log.info("lifespan.redis_offline_fallback", host=redis_host, port=redis_port)

    # Initialize Chroma (or fallback to numpy store)
    if chroma_ok is True:
        app.state.chroma_heartbeat = _chroma_heartbeat_factory(chroma_host, chroma_port)
        log.info("lifespan.chroma_connected", host=chroma_host, port=chroma_port)
    else:
        app.state.chroma_heartbeat = None
        log.info("lifespan.chroma_offline_fallback", host=chroma_host, port=chroma_port)

    # 2. Initialize Agents & Repositories (Step 5.1)
    llm = get_llm(settings)
    cache = (
        RedisParseCache(app.state.redis, ttl_s=settings.parse_cache_ttl_s)
        if app.state.redis is not None
        else InMemoryParseCache()
    )
    repo = get_taxonomy_repository(settings.taxonomy_dir)

    app.state.parsing_agent = ParsingAgent(settings=settings, llm=llm, cache=cache)
    app.state.normalization_agent = NormalizationAgent(settings=settings, llm=llm, repo=repo)
    app.state.matching_agent = MatchingAgent(settings=settings, repo=repo)
    app.state.job_parser = JobParser(llm=llm)
    app.state.search_agent = SearchAgent(settings=settings, llm=llm, repo=repo)
    app.state.coach_agent = CoachAgent(settings=settings, llm=llm, repo=repo)
    app.state.taxonomy_repo = repo

    # 3. Recover stale batch items from previous runs (Step 5.5)
    if app.state.engine is not None and is_db_available():
        await recover_stale_batches(app.state.engine)
    else:
        await recover_stale_batches(None)

    # 4. Pre-seed demo datasets into in-memory store and caches (Exit Criterion 7-B)
    if settings.app_env != "test":
        try:
            from scripts.seed_demo import seed_all

            await seed_all(
                parsing_agent=app.state.parsing_agent,
                matching_agent=app.state.matching_agent,
                search_agent=app.state.search_agent,
                coach_agent=app.state.coach_agent,
            )
        except Exception as exc:
            log.warning("lifespan.seed_demo_skipped", error=str(exc))

    yield

    # 4. Graceful shutdown
    if getattr(app.state, "redis", None) is not None:
        with contextlib.suppress(Exception):
            await app.state.redis.aclose()
    await dispose_engine()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="TalentGraph API",
        version=__version__,
        description="Resume parsing, skill normalization and semantic job matching.",
        lifespan=lifespan,
    )

    # Cross-cutting middleware & handlers
    app.state.limiter = limiter

    # CORS middleware (Step 5.1)
    origins = [settings.web_origin] if settings.web_origin else []
    for origin in ("http://localhost:3000", "http://127.0.0.1:3000"):
        if origin not in origins:
            origins.append(origin)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # RFC 7807 problem+json error handlers
    register_problem_handlers(app)

    # Health & readiness probes
    app.include_router(health.router)

    # V1 API routers (Step 5.4, Step 5.5)
    v1 = APIRouter(prefix="/api/v1")
    v1.include_router(parse.router)
    v1.include_router(batch.router)
    v1.include_router(jobs.router)
    v1.include_router(candidates.router)
    v1.include_router(match.router)
    v1.include_router(skills.router)
    v1.include_router(search.router)
    v1.include_router(coach.router)
    v1.include_router(eval_router.router)

    app.include_router(v1)

    return app


app = create_app()
