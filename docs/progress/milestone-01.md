# Milestone 01: Scope cleanup: progress record

- **Completed by:** Claude Code (agent) for the owner   **Date:** 2026-10-13   **Git SHA:** `a84c6b7`; the 1-D model fix was committed in `43a3d78`. CI is green at `0cdee4b` (run 38409286091)
- **LLM quota used:** 0 requests
- **Status:** ✅ All five exit criteria pass. 1-A and 1-B were re-run at `a84c6b7`; 1-C and 1-D were run once Docker Desktop was up (Docker Engine 29.7.2). The first session couldn't run them (`failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine`).

## Exit criteria results

| # | Check | Command run | Result / metric | Pass? |
|---|---|---|---|---|
| 1-A | Lint, types, tests | `uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest` | `All checks passed!`; `113 files already formatted`; `Success: no issues found in 74 source files`; `53 passed, 2 deselected` (re-run at `a84c6b7` and again after the 1-D model fix) | ✅ |
| 1-B | Nothing removed is still referenced | the grep in `ordered.md` 1-B | No matches (grep exit 1). The re-run first matched three stale, gitignored `__pycache__/*.pyc` files (one for the deleted `llm/ratelimit.py`); after clearing `__pycache__` under `src`/`tests`/`eval` the grep exits 1. Remaining hits elsewhere are Prometheus/Jaeger/OpenTelemetry as taxonomy *skills* in `scripts/` and "idempotent" in `scripts/seed.py` | ✅ |
| 1-C | Stack comes up | `docker compose up -d --build --wait` | Exit 0. `docker compose ps`: `api`, `chroma`, `postgres`, `redis` all `running` / `healthy`, and no other `talentgraph-*` containers exist (no v1 leftovers). Extra checks: `GET /health` → `{"status":"ok","version":"0.1.0","pipeline_version":"1"}`; `GET /ready` → `{"status":"ok","checks":{"db":"ok","redis":"ok","chroma":"ok"}}`; `GET /metrics` → 404 (mount removed) | ✅ |
| 1-D | Migrations round-trip | `docker compose exec api alembic` `current`, `upgrade head`, `downgrade 0001_initial_schema`, `current`, `upgrade head`, `current`; then `alembic check` | All exit 0. The DB was already at `0002_portfolio_rescope (head)`. Downgrade ran `0002 -> 0001` (`current` = `0001_initial_schema`), upgrade ran `0001 -> 0002`. Live tables: `agent_runs, batch_items, batch_jobs, candidate_skills, candidates, emerging_skills, jobs, matches, skill_aliases, skill_implications, skill_relations, skills` (+ `alembic_version`), which matches plan §7.1. No `api_key_id`, `callback_url` or `emerging_skills` review columns remain. `alembic check` first reported drift (see below); after the fix: `No new upgrade operations detected.` | ✅ |
| 1-E | Docs consistent | manual read of `CLAUDE.md`, `README.md`, plan §14, ADR-0003 | No Celery/Flower/Jaeger/Prometheus commands or services remain; D13–D18 added; D1–D12 copied verbatim from `archive/plan-v1.md` | ✅ |

## What changed

- **Docs:**
  - `documents/plan.md` and `documents/ordered.md` rewritten for v2; the v1 copies are in `documents/archive/`.
  - `project-plan-v2.md` marked approved.
  - New: `docs/decisions/ADR-0003-portfolio-rescope.md`.
  - Updated: `CLAUDE.md`, `README.md`.
- **Deleted:**
  - `src/talentgraph/worker/`, `api/webhooks.py`, `api/idempotency.py`, `llm/ratelimit.py`, `observability/tracing.py`, `observability/metrics.py`
  - `deploy/`, `scripts/create_api_key.py`, `scripts/train_section_clf.py`, `eval/api_contract.py`
- **LLM client:** a single model and no shared limiter. A 429 after retries raises `LLMQuotaExceeded`.
- **API:** `/metrics` mount removed.
- **Schema:** `migrations/versions/0002_portfolio_rescope.py`:
  - drops `webhook_deliveries`, `batch_jobs.callback_url`, `api_keys` and the `api_key_id` columns on `candidates`, `jobs` and `batch_jobs`
  - drops `emerging_skills.{status, merged_into, reviewed_by, reviewed_at}`

  Downgrade restores them (`api_key_id` comes back nullable). `db/models.py` and `test_models_schema.py` were updated to match.
- **Settings:**
  - removed `CELERY_*`, `LLM_FALLBACK_MODEL`, `LLM_RPM_LIMIT`, `LLM_RPD_LIMIT`, `DEFAULT_RATE_LIMIT_PER_MIN`, `MAX_INFLIGHT_PER_KEY`, `WEBHOOK_MAX_ATTEMPTS`, `OTEL_*`
  - added `API_KEY` (blank = no key) and `RATE_LIMIT_PER_MIN`
  - `MAX_BATCH_FILES` is now 20
  - tests updated (`test_config.py`: the fallback-model test was replaced by a blank-`API_KEY` test)
- **Dependencies:**
  - removed celery, flower, pdfplumber, prometheus-client and opentelemetry-*
  - scikit-learn moved to dev
  - `uv lock` / `uv sync` uninstalled the removed packages and their transitive dependencies
- **Compose:** `worker`, `flower`, `jaeger` and `prometheus` removed; the `x-app` anchor was inlined into `api`.
- **Stubs:**
  - every stub docstring now names its v2 step
  - new stubs: `parsing/verify.py`, `matching/blind.py`, `agents/search/`, `agents/coach/`, `routers/search.py`, `routers/coach.py`, `scripts/finetune_embeddings.py`, `eval/fairness.py`, `eval/search.py`, `eval/coach.py`
  - `config/matching.yaml` dropped `gamma_semantic` (α 0.70 / β 0.30)
  - `config/proficiency.yaml` dropped the recency, breadth and certification rules

## Deviations from plan

- **ORM/migration drift fixed during 1-D:** `alembic check` reported `remove_index ix_emerging_skills_normalized_text` + `add_constraint UniqueConstraint(normalized_text)`. Migration `0001` creates a unique *index*, but `EmergingSkill.normalized_text` was declared `unique=True` only, which autogenerate reads as a unique *constraint*. This dates from Milestone 0, not `0002`. Uniqueness held either way. Fix: `db/models.py:85` is now `unique=True, index=True`, matching `skills.slug` and `skill_aliases.alias_normalized`. No migration was needed. The api image was rebuilt and `alembic check` is clean.

- **slowapi and auth:** `project-plan-v2.md` listed "replace `api/ratelimit.py` with slowapi" under Milestone 1. Both `api/ratelimit.py` and `api/auth.py` were docstring-only stubs, so this milestone re-pointed them at Steps 5.2–5.3 and added the settings. The `slowapi` dependency is added in Step 5.3, when it is first used.

## Known issues / follow-ups

- **Build time:** any change under `src/` makes the api image rebuild take about 10 minutes. The builder re-runs `uv sync`, the embedding-model download and the venv copy (Dockerfile lines 10–22). Worth splitting those layers if it slows iteration.
- **Local `.env`:** the owner's local `.env` (not in git) still holds the removed variables (`CELERY_*`, `LLM_FALLBACK_MODEL`, …). They are ignored (`extra="ignore"`), but should be cleaned up against `.env.example`. Add `API_KEY=` there too.
- **0-H** (CI green) still needs a pushed branch. `ci.yml` needed no changes for the re-scope.
- `core/schemas/messages.py` still has the v1 `AgentMessage` envelope; Step 4.6 simplifies it (plan §5).

## Handoff notes for the next milestone

- Milestone 2 starts at Step 2.1 (the `ParsedResume` schema with `evidence` / `verified`). Check that all Phase 1 `.gt.json` files still validate after the schema change.
- Recording FakeLLM fixtures (Step 2.9) needs a real `GEMINI_API_KEY` and uses free-tier quota. Use synthetic resumes only.
