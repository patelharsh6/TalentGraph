# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status and planning docs

TalentGraph is a portfolio project for AI/ML engineering roles: a multi-agent system with a Next.js front end and a live demo. LangGraph orchestrates the agents, and a FastAPI REST API exposes them.

The three core agents:

- **Parsing:** turns PDF, DOCX or TXT resumes into structured data. Every LLM field cites its source text, and a verifier checks it (F2).
- **Skill normalization:** maps skills to a hierarchical taxonomy, using fine-tuned embeddings (F5).
- **Matching:** scores candidates against jobs semantically, explains the score, and can run blind (F4).

Two more agents build on them: **Talent Search** (natural-language search, tool calling; F1) and **Career Coach** (generate, critique, revise; F3).

The project was re-scoped on 2026-10-13 (ADR-0003). The 12 v1 phases became milestones 0–8:

- Milestone 0 (v1 Phases 0–1: scaffolding, data foundation) is done; 0-H (CI green) waits on the owner pushing a branch.
- Milestone 1 (scope cleanup) is done except the Docker checks.
- Milestone 2 (Parsing Agent + F2) is next.

Most agent modules under `src/talentgraph/` are still docstring-only stubs that name the `ordered.md` step (e.g. "Step 2.10") that implements them.

Read these documents (in `documents/`) before you make design decisions:

1. `idea.md`: the original challenge brief. It is the starting point for requirements; the v2 deviations are in plan §14.
2. `plan.md`: the v2 design. It covers architecture, agent algorithms, the data model, the API contract, the web app, the metric targets M1–M10 and the decision log (§14).
3. `ordered.md`: the build order. It splits the work into milestones 0–8, each with exit criteria, and has a status tracker at the top.
4. `status.md`: what is done and pending, step by step, plus owner actions and the metrics scoreboard. Keep it current: update it whenever a step or exit criterion changes state.
5. `project-plan-v2.md`: the one-page summary of the re-scope. `archive/` holds the v1 plan and build order; "Phase 1.x" references in `scripts/` and in `docs/progress/phase-0*.md` point there.

Rules for working through the milestones:

- Work milestones strictly in order. The exception: Milestone 7 (web app) may start once Milestone 5's OpenAPI is stable.
- A milestone is done only when every exit criterion has been run and recorded in `docs/progress/milestone-NN.md`, using the template at the end of `ordered.md`.
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

docker compose up -d --build              # api :8000, postgres, redis, chroma :8001
                                          # host ports for postgres/redis come from POSTGRES_HOST_PORT / REDIS_HOST_PORT in .env
uv run alembic revision --autogenerate -m "msg" && uv run alembic upgrade head
uv run uvicorn talentgraph.api.main:app --reload

# Phase 1 data (see data/README.md)
uv run python data/taxonomy/raw/download.py          # pinned O*NET 31.0 tables -> data/taxonomy/raw/onet/
uv run python scripts/regenerate_data.py [--check]   # taxonomy, profiles, resumes, jobs, gold sets (--check: 1-I)
uv run python scripts/seed.py --stats                # taxonomy stats + 1-A (each data script has --stats)
docker compose run --rm --no-deps -v "$PWD/scripts:/app/scripts:ro" -v "$PWD/data/taxonomy:/app/data/taxonomy:ro" api python scripts/seed.py --taxonomy
```

The default pytest `addopts` exclude the `integration`, `e2e`, `llm` and `slow` markers.

## Architecture notes that span files

- **Settings:** `config.py` is the only place that reads environment variables. Every new variable also goes in `.env.example`.
- **LLM access:** all LLM calls go through `llm/client.py` (`get_llm()`).
  - The provider is the Google Gemini free tier, through the `google-genai` SDK: `client.aio.models.generate_content` with `response_mime_type="application/json"` and `response_json_schema=Model.model_json_schema()`. The response is then validated with Pydantic.
  - `LLM_MODE` is one of `real`, `fake` or `stub`. `real` without `GEMINI_API_KEY` falls back to `FakeLLM` (`llm/fake.py`), which serves fixtures from `tests/fixtures/llm/<Schema>/<hash>.json`.
  - One model (`LLM_MODEL`), with retries and a per-process semaphore. A 429 that survives the retries raises `LLMQuotaExceeded`; agents must then degrade to rules-only output (`status="partial"`). There is no fallback model and no cross-process quota counter (D17).
  - Never send real resumes to the free tier: Google may use free-tier prompts. The demo leads with cached sample data.
- **Contracts:** every cross-component contract lives in `core/schemas/`. That includes the agent result types and `ParsedResume`, `SkillProfile` and `MatchResult`, which the API also returns.
- **Errors:** errors subclass `core/errors.TalentGraphError` (`code`, `http_status`, `retryable`). `api/problems.py` renders them as RFC 7807 `application/problem+json`.
- **API access:** one key from `API_KEY` in the `X-API-Key` header on write endpoints; a blank key disables auth for local dev. Rate limits come from slowapi, per IP. There are no key scopes, no per-key data ownership, no webhooks and no idempotency keys (ADR-0003).
- **Background work:** batches (≤ `MAX_BATCH_FILES`, 20) run on FastAPI `BackgroundTasks` in the API process; progress is kept in `batch_jobs` / `batch_items`. Celery was removed (D14).
- **Caching:** Redis holds the parse, JD, search-plan and coach caches. Every key includes `PIPELINE_VERSION`.
- **Embeddings and vectors:** `embeddings/encoder.py` is a lazy process-wide singleton (sentence-transformers, CPU). Vector search goes through the `VectorStore` protocol: `ChromaVectorStore` at runtime, `NumpyVectorStore` in tests. The F5 fine-tuned model replaces the base model through `EMBEDDING_MODEL`.
- **Versioning:** `PIPELINE_VERSION` in `talentgraph/__init__.py` is part of every cache key. Bump it when parser, normalizer or embedding-model output changes.
- **Observability:** structlog JSON logs plus the `agent_runs` table, returned to callers with `?include=trace`. There is no OpenTelemetry or Prometheus (ADR-0003).
- **Front end:** the Next.js app lives in `web/` (Milestone 7). It uses a typed client generated from `/openapi.json`, and a server-side route handler adds the API key.
- **Torch:** `pyproject.toml` pulls CPU-only torch wheels on Linux (Docker) through a uv index.
- **mypy:** pinned below 2.x because Windows Application Control blocks mypy 2's native parser DLL on this machine.
- **Native torch:** the same policy blocks torch's `_C` DLL on this machine. Anything that loads the encoder runs in the api container (or Colab, for fine-tuning), not natively: taxonomy seeding, embedding code, F5 training. Unit tests never load torch.
- **Data:** `data/` is generated by `scripts/` from fixed seeds and is byte-for-byte reproducible. JSON/CSV/YAML is committed; `data/resumes/` and `data/taxonomy/raw/onet/` are not. Taxonomy sources and their licenses are in `data/taxonomy/ATTRIBUTION.md` (ADR-0001). The match gold comes from a rubric labeler, not an LLM judge (ADR-0002), and must be re-validated before Milestone 4 sign-off. ADR-0004 adds report-only supplements: LLM-reworded resumes, a consented real-resume set in `data/private/` (gitignored, never committed or published beyond aggregate scores), the TechWolf ESCO skill benchmark and USAJOBS / `data_jobs` postings in `data/external/raw/` (gitignored). Pass/fail is always decided on the synthetic test split.
- **Unit tests are offline:** `tests/conftest.py` blocks non-loopback sockets unless a test is marked `integration`, `e2e` or `llm`.
