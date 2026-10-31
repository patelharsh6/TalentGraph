"""FastAPI application. Run with `uvicorn talentgraph.api.main:app`."""

import contextlib
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager

import structlog
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis

from talentgraph import __version__
from talentgraph.agents.matching.agent import MatchingAgent
from talentgraph.agents.matching.job_parser import JobParser
from talentgraph.agents.normalization.agent import NormalizationAgent
from talentgraph.agents.parsing.agent import ParsingAgent
from talentgraph.agents.parsing.cache import InMemoryParseCache, RedisParseCache
from talentgraph.api.problems import register_problem_handlers
from talentgraph.api.ratelimit import limiter
from talentgraph.api.routers import (
    batch,
    candidates,
    health,
    jobs,
    match,
    parse,
    skills,
)
from talentgraph.config import get_settings
from talentgraph.db.repositories.taxonomy import get_taxonomy_repository
from talentgraph.db.session import dispose_engine, init_engine
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

    # 1. Initialize databases and caches (with resilient fallbacks if offline)
    try:
        app.state.engine = init_engine(settings.database_url)
    except Exception as exc:
        log.warning("lifespan.db_init_warning", error=str(exc))
        app.state.engine = None

    try:
        app.state.redis = Redis.from_url(settings.redis_url)
    except Exception as exc:
        log.warning("lifespan.redis_init_warning", error=str(exc))
        app.state.redis = None

    app.state.chroma_heartbeat = _chroma_heartbeat_factory(
        settings.chroma_host, settings.chroma_port
    )

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
    app.state.taxonomy_repo = repo

    # 3. Recover stale batch items from previous runs (Step 5.5)
    await recover_stale_batches(app.state.engine)

    yield

    # 4. Graceful shutdown
    if app.state.redis is not None:
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
    origins = [settings.web_origin] if settings.web_origin else ["*"]
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
    # Milestone 6 will add: search.router, coach.router

    app.include_router(v1)

    return app


app = create_app()
