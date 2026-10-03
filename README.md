# TalentGraph

TalentGraph is a multi-agent AI system. It does four things:

- parses resumes in PDF, DOCX or TXT
- normalizes skills against a hierarchical taxonomy
- matches candidates to job descriptions semantically
- exposes everything through a documented REST API

| Document | What it covers |
|---|---|
| [`idea.md`](idea.md) | The problem statement and requirements |
| [`plan.md`](plan.md) | Architecture and design decisions |
| [`ordered.md`](ordered.md) | Phase-by-phase build order, with exit criteria and a status tracker |

> **Status:** Phase 0 (scaffolding). Most modules are stubs that state which phase implements them.

> ⚠️ **Gemini free tier:** Google can use prompts sent on the free tier to improve its products. Only send synthetic or consented resumes. A paid key is needed before you process real personal data.

## Stack

- Python 3.12, managed with uv
- FastAPI for the API, LangGraph for the agent pipeline
- Google Gemini API, free tier, through `google-genai`
- sentence-transformers for embeddings, ChromaDB for vector search
- PostgreSQL for data, Redis with Celery for background workers
- Docker Compose for running the whole stack

## Quick start (Docker)

```bash
cp .env.example .env                 # then set GEMINI_API_KEY (optional: without it the LLM runs in fake mode)
docker compose up -d --build
curl localhost:8000/health
curl localhost:8000/ready
open http://localhost:8000/docs      # Swagger UI
```

The Docker Compose stack runs these services:

| Service | Port |
|---|---|
| `api` | `8000` |
| `worker` (Celery) | n/a |
| `postgres` | `5432` |
| `redis` | `6379` |
| `chroma` | `8001` |
| `jaeger` | `16686` (UI) |
| `prometheus` | `9090` |

Flower, a web UI for watching the Celery workers, is optional: `docker compose --profile tools up -d flower`, then open port `5555`.

## Local development (without Docker for the app)

```bash
uv sync                                                      # install deps into .venv
docker compose up -d postgres redis chroma                   # infra only
# in .env, point hosts at localhost (DATABASE_URL, REDIS_URL, CHROMA_HOST=localhost, CHROMA_PORT=8001, CELERY_*)
uv run alembic upgrade head
uv run uvicorn talentgraph.api.main:app --reload
uv run celery -A talentgraph.worker.celery_app worker --pool=solo -l info   # --pool=solo is required on Windows
```

## Quality checks

```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy
uv run pytest                          # unit tests only (offline, FakeLLM)
uv run pytest tests/unit/test_errors.py::test_error_defaults   # a single test
uv run pytest -m integration           # needs the compose stack
uv run pytest -m llm                   # real Gemini calls (uses free quota)
```
