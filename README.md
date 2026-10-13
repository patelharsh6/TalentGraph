# TalentGraph

TalentGraph is a multi-agent AI system for talent intelligence. It does these things:

- **parses** resumes in PDF, DOCX or TXT; every LLM-extracted field cites its source text, and a verifier checks it
- **normalizes** skills against a 9,600-skill hierarchical taxonomy, using fine-tuned embeddings
- **matches** candidates to jobs semantically, with a requirement-by-requirement explanation, gap analysis and a blind-screening mode
- **searches** candidates in plain English, through an agent that calls tools
- **coaches** candidates with a learning plan, interview questions and truthful resume suggestions, checked by a critic step

Everything runs behind a documented REST API and a Next.js web app. Quality is measured (metrics M1–M10) and published.

| Document | What it covers |
|---|---|
| [`project-plan-v2.md`](documents/project-plan-v2.md) | One-page summary of the current plan |
| [`plan.md`](documents/plan.md) | Architecture, agent designs, API, metrics and the decision log |
| [`status.md`](documents/status.md) | What is done and pending, step by step |
| [`ordered.md`](documents/ordered.md) | Milestone-by-milestone build order, with exit criteria and a status tracker |
| [`idea.md`](documents/idea.md) | The original challenge brief |

> **Status:** Milestone 0 (scaffolding and data foundation) and Milestone 1 (scope cleanup) are implemented; see `docs/progress/`. The agents are still stubs that name the build step that implements them. The taxonomy, synthetic corpora and gold sets are described in [`data/README.md`](data/README.md).

> ⚠️ **Gemini free tier:** Google can use prompts sent on the free tier to improve its products. Only send synthetic or consented resumes. A paid key is needed before you process real personal data.

## Stack

- Python 3.12 with uv; FastAPI; LangGraph for the agents
- Google Gemini API (free tier) through `google-genai`
- sentence-transformers for embeddings (fine-tuned on the taxonomy), ChromaDB for vector search
- PostgreSQL for data, Redis for caching
- Next.js + Tailwind for the web app (Milestone 7)
- Docker Compose for the backend stack; GitHub Actions for CI and the eval gate

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
| `postgres` | `5432` |
| `redis` | `6379` |
| `chroma` | `8001` |

## Local development (without Docker for the app)

```bash
uv sync                                                      # install deps into .venv
docker compose up -d postgres redis chroma                   # infra only
# in .env, point hosts at localhost (DATABASE_URL, REDIS_URL, CHROMA_HOST=localhost, CHROMA_PORT=8001)
uv run alembic upgrade head
uv run uvicorn talentgraph.api.main:app --reload
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
