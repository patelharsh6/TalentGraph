# Phase 00: Foundation & scaffolding: progress record

- **Completed by:** Claude Code (agent) for the owner   **Date:** 2026-10-03   **Git SHA:** uncommitted (on top of `88dff78`)
- **LLM quota used:** 0 requests (no `GEMINI_API_KEY` configured; the live `llm` test skipped)
- **Status:** 🟨 Every criterion that can run locally passes. **0-H (CI green) is pending**: it needs the owner to push a branch.

## Exit criteria results

| # | Check | Command run | Result / metric | Pass? |
|---|---|---|---|---|
| 0-A | Lint and types | `uv run ruff check . && uv run ruff format --check . && uv run mypy src` | `All checks passed!`; `108 files already formatted`; `Success: no issues found in 73 source files` (all exit 0) | ✅ |
| 0-B | Unit tests offline | `uv run pytest` (an autouse guard in `tests/conftest.py` refuses non-loopback sockets) | `52 passed, 2 deselected in 6.58s`, covering settings, schemas, FakeLLM, NumpyVectorStore, errors, API health, ORM tables and the Phase 1 data tests. A throwaway test that connected to `1.1.1.1:443` got `RuntimeError: unit tests must not use the network` | ✅ |
| 0-C | Stack comes up | `docker compose build`, `docker compose down`, then a timed `docker compose up -d --wait`, then `docker compose ps` | `up --wait exit=0 after 32s`; api, worker, postgres, redis, chroma, jaeger and prometheus all `(healthy)` | ✅ |
| 0-D | Liveness and readiness | `curl localhost:8000/health`, `curl localhost:8000/ready` | `{"status":"ok","version":"0.1.0","pipeline_version":"1"} [200]`; `{"status":"ok","checks":{"db":"ok","redis":"ok","chroma":"ok"}} [200]` | ✅ |
| 0-E | Migrations apply cleanly | `docker compose exec api alembic upgrade head`, then `downgrade base`, then `upgrade head` | exit 0 / 0 / 0. `pg_tables` lists 14 tables plus `alembic_version`: agent_runs, api_keys, batch_items, batch_jobs, candidate_skills, candidates, emerging_skills, jobs, matches, skill_aliases, skill_implications, skill_relations, skills, webhook_deliveries (all of plan §7.1) | ✅ |
| 0-F | OpenAPI served | `GET /openapi.json`, `GET /docs` | `[200]`, `[200]` | ✅ |
| 0-G | LLM wrapper is safe | `uv run pytest tests/unit/test_fake_llm.py tests/unit/test_config.py`; `uv run pytest -m llm` | `get_llm()` returns `FakeLLM` without a key (unit tests pass, including the new blank-key case). `-m llm`: `SKIPPED: GEMINI_API_KEY is not set` (allowed: the live half is optional without a key) | ✅ |
| 0-H | CI green | push a branch (owner only) | **Not run.** The agent never commits or pushes. `ci.yml` parses and has jobs `checks` and `integration` | ⏳ pending owner |
| 0-I | Celery worker | `docker compose exec worker celery -A talentgraph.worker.celery_app inspect ping`; `send_task('talentgraph.ping').get()` | `pong` / `1 node online.`; `talentgraph.ping -> pong` | ✅ |

## Iteration log (metrics phases only)

| Iteration | Change | Metric before → after |
|---|---|---|
| n/a | n/a | n/a |

## Deviations from plan

- **Compose healthchecks:** chroma (bash `/dev/tcp` → `/api/v2/heartbeat`), jaeger (`:14269/`) and prometheus (`/-/healthy`) had none, so 0-C ("all services healthy") could not pass. All three now have one, and app services wait for `chroma: service_healthy`.
- **Configurable host ports:** `POSTGRES_HOST_PORT` / `REDIS_HOST_PORT` were added to `.env.example` (defaults 5432 / 6379). On this machine a native PostgreSQL holds 5432 and another Redis holds 6379, so the local `.env` uses 5434 / 6381. In-container URLs are unchanged.
- **Blank-key bug fixed:** `GEMINI_API_KEY=` (blank, as in `.env.example`) used to be read as an empty `SecretStr`. `get_llm()` then chose the real Gemini client with no key instead of FakeLLM. `config.py` now treats a blank key as `None`, with a regression test.
- **Tests added:**
  - `tests/integration/test_taxonomy_parity.py` (also needed so CI's `pytest -m integration` doesn't exit 5 with "no tests collected")
  - `tests/integration/test_llm_live.py` (marked `llm`, skips without a key)
  - the offline network guard in `tests/conftest.py`
- **CI:** the integration job now seeds the taxonomy before `pytest -m integration`.
- **`VectorStore.ids()`:** added to the protocol and both implementations, so the seeder can prune stale vectors.

## Known issues / follow-ups

- **0-H** needs a pushed branch. CI hasn't been observed running, so the `integration` job (compose `--wait`, seed in container, parity test) is unverified on GitHub runners.
- The api logs `Transient error ... exporting spans batch` against jaeger even though `OTEL_ENABLED=false`. Phase 8 should check that the tracing setup honours the flag.
- Right after `up --wait` returned, host `curl` saw one connection failure (`[000]`) before Docker Desktop's port-forward was ready. A retry seconds later returned 200. This is a Windows/Docker Desktop artifact, not an app issue.
- Windows Application Control blocks torch's native DLL (as it already did for mypy 2.x). Anything that loads the encoder must run in a container on this machine.

## Handoff notes for the next phase

- **Local `.env`** (gitignored) was created from `.env.example` with `POSTGRES_HOST_PORT=5434` and `REDIS_HOST_PORT=6381`. Native tools reach the stack at `localhost:5434` (Postgres), `localhost:6381` (Redis) and `localhost:8001` (Chroma).
- **Integration tests run natively** with `DATABASE_URL=postgresql+asyncpg://talentgraph:talentgraph@localhost:5434/talentgraph CHROMA_HOST=localhost CHROMA_PORT=8001 uv run pytest -m integration`.
- `alembic downgrade base` empties the taxonomy tables. Re-run the seeder afterwards (see `data/README.md`).
