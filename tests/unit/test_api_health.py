from fastapi import FastAPI
from fastapi.testclient import TestClient

from talentgraph.api.problems import register_problem_handlers
from talentgraph.api.routers import health
from talentgraph.core.errors import FileTooLarge


def _app() -> FastAPI:
    # Built without the lifespan so the test needs no DB/Redis/Chroma.
    app = FastAPI()
    register_problem_handlers(app)
    app.include_router(health.router)

    @app.get("/boom")
    async def boom() -> None:
        raise FileTooLarge("11 MB > 10 MB")

    return app


def test_health_ok() -> None:
    res = TestClient(_app()).get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_errors_are_problem_json() -> None:
    res = TestClient(_app()).get("/boom")
    assert res.status_code == 413
    assert res.headers["content-type"].startswith("application/problem+json")
    assert res.json()["type"].endswith("/file_too_large")
