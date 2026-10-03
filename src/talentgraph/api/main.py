"""FastAPI application. Run with `uvicorn talentgraph.api.main:app`."""

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from prometheus_client import make_asgi_app
from redis.asyncio import Redis

from talentgraph import __version__
from talentgraph.api.problems import register_problem_handlers
from talentgraph.api.routers import health
from talentgraph.config import get_settings
from talentgraph.db.session import dispose_engine, init_engine
from talentgraph.observability.logging import configure_logging


def _chroma_heartbeat_factory(host: str, port: int) -> Callable[[], int]:
    def heartbeat() -> int:
        import chromadb

        return int(chromadb.HttpClient(host=host, port=port).heartbeat())

    return heartbeat


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.log_level)
    app.state.engine = init_engine(settings.database_url)
    app.state.redis = Redis.from_url(settings.redis_url)
    app.state.chroma_heartbeat = _chroma_heartbeat_factory(
        settings.chroma_host, settings.chroma_port
    )
    # Phase 5.6: build the AgentRegistry, warm the Encoder, and call registry.startup() here.
    yield
    await app.state.redis.aclose()
    await dispose_engine()


def create_app() -> FastAPI:
    app = FastAPI(
        title="TalentGraph API",
        version=__version__,
        description="Resume parsing, skill normalization and semantic job matching.",
        lifespan=lifespan,
    )
    register_problem_handlers(app)
    app.include_router(health.router)

    v1 = APIRouter(prefix="/api/v1")
    # Phase 6/7: v1.include_router(parse.router), batch, jobs, candidates, match, skills
    app.include_router(v1)

    app.mount("/metrics", make_asgi_app())
    return app


app = create_app()
