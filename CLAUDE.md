# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status and planning docs

TalentGraph is a multi-agent system with three agents:

- **Parsing:** turns PDF, DOCX or TXT resumes into structured data.
- **Skill normalization:** maps skills to a hierarchical taxonomy.
- **Matching:** scores candidates against jobs semantically.

LangGraph orchestrates them, and a FastAPI REST API exposes the pipeline. The repo is in **Phase 0 (scaffolding)**. Most modules under `src/talentgraph/` are docstring-only stubs that name the `ordered.md` step that implements them.

Read these documents before you make design decisions:

1. `idea.md`: the original brief. It is the source of truth for requirements.
2. `plan.md`: the design. It covers architecture, the agent message protocol, the agent algorithms, the data model, the API contract, the metric targets M1–M6 and the decision log (§14).
3. `ordered.md`: the build order. It splits the work into phases 0–11, each with exit criteria, and has a status tracker at the top.

Rules for working through the phases:

- Work phases strictly in order.
- A phase is done only when every exit criterion has been run and recorded in `docs/progress/phase-NN.md`, using the template at the end of `ordered.md`.
- Don't lower a metric target without an ADR in `docs/decisions/` and a new row in plan §14. Old rows are superseded, never edited.
- **Never commit or push.** The owner does all git operations.

## Commands

```bash
uv sync                                   # install (Python 3.12, uv-managed .venv)
uv run ruff check . && uv run ruff format --check .
uv run mypy                               # strict; config in pyproject.toml
uv run pytest                             # unit tests only: offline, FakeLLM, no services
uv run pytest tests/unit/test_errors.py::test_error_defaults   # single test
uv run pytest -m integration              # needs `docker compose up -d`
uv run pytest -m llm                      # real Gemini calls; uses free-tier quota

docker compose up -d --build              # full stack: api :8000, worker, postgres, redis, chroma :8001, jaeger :16686, prometheus :9090
docker compose --profile tools up -d flower   # Celery UI :5555
uv run alembic revision --autogenerate -m "msg" && uv run alembic upgrade head
uv run uvicorn talentgraph.api.main:app --reload
uv run celery -A talentgraph.worker.celery_app worker --pool=solo -l info   # Windows needs --pool=solo
```

The default pytest `addopts` exclude the `integration`, `e2e`, `llm` and `slow` markers.

## Architecture notes that span files

- **Settings:** `config.py` is the only place that reads environment variables. Every new variable also goes in `.env.example`.
- **LLM access:** all LLM calls go through `llm/client.py` (`get_llm()`).
  - The provider is the Google Gemini free tier, through the `google-genai` SDK: `client.aio.models.generate_content` with `response_mime_type="application/json"` and `response_json_schema=Model.model_json_schema()`. The response is then validated with Pydantic.
  - `LLM_MODE` is one of `real`, `fake` or `stub`. `real` without `GEMINI_API_KEY` falls back to `FakeLLM` (`llm/fake.py`), which serves fixtures from `tests/fixtures/llm/<Schema>/<hash>.json`.
  - Free-tier quotas are enforced across processes by `llm/ratelimit.py` (Redis RPM/RPD counters). When the quota runs out, the client switches to `LLM_FALLBACK_MODEL`; if that fails too, it raises `LLMQuotaExceeded`. Agents must then degrade to rules-only output (`status="partial"`).
  - Never send real resumes to the free tier: Google may use free-tier prompts.
- **Contracts:** every cross-component contract lives in `core/schemas/`. That includes `AgentMessage` (the shared message protocol) and `ParsedResume`, `SkillProfile` and `MatchResult`, which the API also returns.
- **Errors:** errors subclass `core/errors.TalentGraphError` (`code`, `http_status`, `retryable`). `api/problems.py` renders them as RFC 7807 `application/problem+json`.
- **Background work:** runs on Celery (`worker/celery_app.py`, tasks in `worker/tasks.py`), with Redis as the broker.
  - Tasks are synchronous and run async code with `asyncio.run()`.
  - The DB engine, encoder and agents are created per process in `worker_process_init`. Never share an async engine across a fork.
  - `acks_late` is on, so tasks must be idempotent.
- **Embeddings and vectors:** `embeddings/encoder.py` is a lazy process-wide singleton (sentence-transformers, CPU). Vector search goes through the `VectorStore` protocol: `ChromaVectorStore` at runtime, `NumpyVectorStore` in tests.
- **Versioning:** `PIPELINE_VERSION` in `talentgraph/__init__.py` is part of every cache key. Bump it when parser or normalizer output changes.
- **Torch:** `pyproject.toml` pulls CPU-only torch wheels on Linux (Docker) through a uv index.
- **mypy:** pinned below 2.x because Windows Application Control blocks mypy 2's native parser DLL on this machine.
