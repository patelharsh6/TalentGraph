# TalentGraph: Ordered Execution Guide

> **Status note (2026-10-03):** Phases 0 and 1 are implemented and their exit criteria are recorded in `docs/progress/`. Phase 0 stays 🟨 only until CI (0-H) runs green on a pushed branch. Phase 1 rebuilt the taxonomy from O\*NET 31.0 + Wikidata (ADR-0001) and generates its datasets without LLM calls (ADR-0002).
>
> **What this is.** This guide is the step-by-step build order for TalentGraph, split into **12 phases (0–11)**. Each phase lists its goal, prerequisites, detailed steps, deliverables and **exit criteria**. The exit criteria are objective checks that must all pass before the phase counts as complete.
>
> **Read first:** [`idea.md`](idea.md) (the requirements) and [`plan.md`](plan.md) (the design). Section references such as "plan §6.2" point into `plan.md`.

---

## How to use this document (for humans and agents)

1. **Work strictly in order.** Do not start phase *N+1* until every exit criterion of phase *N* is ✅. Inside a phase, steps can run in parallel unless one is marked **(after X.Y)**.
2. **Before you start a phase**, read its "Depends on" list and confirm those phases have a progress record in `docs/progress/`.
3. **When you finish a phase**, run the whole exit-criteria checklist and create `docs/progress/phase-NN.md` from the [template](#progress-record-template). Paste the commands you ran and their real output or metric values. Never write ✅ for a check that you didn't run.
4. **If a criterion can't be met**, don't lower the bar quietly. Write down what you tried, open an ADR in `docs/decisions/`, add a row to plan §14, and then adjust the target.
5. **Update the [Status Tracker](#status-tracker)** below whenever a phase starts or finishes.
6. **Global rules** apply to every phase:
   - `uv run ruff check . && uv run ruff format --check .` passes.
   - `uv run mypy src` passes (strict).
   - `uv run pytest` passes offline in under 60 s (unit tests only; FakeLLM, no network).
   - No secrets in git. New env vars are added to `.env.example` and `config.py`.
   - `CLAUDE.md` is updated if commands or architecture change.
   - **Don't commit or push.** The project owner does all git commits.
   - **Free-tier hygiene:** never send real resumes to the Gemini free tier, and record roughly how much LLM quota a phase used in its progress record.

### Status tracker

| Phase | Name | Status | Progress record |
|---|---|---|---|
| 0 | Foundation & scaffolding | 🟨 All exit criteria pass except 0-H (CI green), which needs the owner to push a branch | [phase-00](../docs/progress/phase-00.md) |
| 1 | Data foundation: taxonomy & datasets | ✅ Complete (2026-10-03; human κ pending, allowed by 1-H) | [phase-01](../docs/progress/phase-01.md) |
| 2 | Parsing Agent | ⬜ Not started | n/a |
| 3 | Skill Normalization Agent | ⬜ Not started | n/a |
| 4 | Semantic Matching Agent | ⬜ Not started | n/a |
| 5 | Multi-Agent Orchestrator | ⬜ Not started | n/a |
| 6 | Core REST API (sync endpoints, auth, limits, errors) | ⬜ Not started | n/a |
| 7 | Async batch processing & webhooks | ⬜ Not started | n/a |
| 8 | Observability | ⬜ Not started | n/a |
| 9 | SDKs, examples & documentation | ⬜ Not started | n/a |
| 10 | System evaluation & hardening | ⬜ Not started | n/a |
| 11 | Release & stretch goals | ⬜ Not started | n/a |

Legend: ⬜ Not started · 🟨 In progress · ✅ Complete · ⛔ Blocked (give the reason in the progress record)

### Dependency graph

```
0 ─▶ 1 ─▶ 2 ─▶ 3 ─▶ 4 ─▶ 5 ─▶ 6 ─▶ 7 ─▶ 8 ─▶ 9 ─▶ 10 ─▶ 11
           └────────(3 needs taxonomy from 1; 4 needs gold sets from 1)
```

Phase 8 (observability) relies on the hooks that Phase 5 adds. Phase 9 can begin once Phase 7's OpenAPI is stable.

---

## Phase 0: Foundation & scaffolding

**Goal:** a runnable, tested and containerized empty skeleton that every later phase builds on.
**Depends on:** nothing.

### Steps

**0.1 Initialize the project.**
- Run `uv init --package talentgraph --python 3.12`, then move the package to the `src/talentgraph/` layout (plan §11).
- Add runtime dependencies: `fastapi`, `uvicorn[standard]`, `pydantic>=2`, `pydantic-settings`, `sqlalchemy[asyncio]>=2`, `asyncpg`, `alembic`, `redis`, `celery[redis]`, `chromadb`, `sentence-transformers`, `pymupdf`, `pdfplumber`, `python-docx`, `rapidfuzz`, `dateparser`, `phonenumbers`, `langgraph`, `google-genai`, `tenacity`, `structlog`, `prometheus-client`, `opentelemetry-sdk`, `opentelemetry-exporter-otlp`, `opentelemetry-instrumentation-fastapi`, `opentelemetry-instrumentation-celery`, `httpx`, `torch` (CPU wheels on Linux through a uv index), `python-multipart`, `pyyaml`, `scikit-learn`, `numpy`.
- Add dev dependencies: `pytest`, `pytest-asyncio`, `pytest-cov`, `ruff`, `mypy`, `pre-commit`, `locust`, `faker`, `reportlab`, `openapi-spec-validator`, `scipy`, `flower`.

**0.2 Configure tooling** in `pyproject.toml`:
- **ruff:** line length 100, rule sets `E,F,I,B,UP,SIM,ASYNC`.
- **mypy:** `strict = true` for `src/`.
- **pytest:**
  - markers `unit`, `integration`, `e2e`, `llm`, `slow`
  - `addopts = "-m 'not integration and not e2e and not llm and not slow'"`
  - `asyncio_mode = "auto"`
- **pre-commit:** add a `.pre-commit-config.yaml` that runs ruff and mypy.

**0.3 Settings.** Create `src/talentgraph/config.py` with a `Settings(BaseSettings)` class covering:
- `DATABASE_URL`, `REDIS_URL`, `CHROMA_HOST`, `CHROMA_PORT`
- `GEMINI_API_KEY` (optional), `LLM_MODE=real|fake|stub`, `LLM_MODEL=gemini-3.8-flash`, `LLM_FALLBACK_MODEL=gemini-3.5-flash-lite`, `LLM_TIMEOUT_S=8`, `LLM_MAX_CONCURRENCY=4`, `LLM_RPM_LIMIT`, `LLM_RPD_LIMIT`, `LLM_STUB_LATENCY_MS`
- `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, `CELERY_CONCURRENCY`
- `EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2`
- `MAX_UPLOAD_MB=10`, `MAX_BATCH_FILES=100`, `DEFAULT_RATE_LIMIT_PER_MIN=60`
- `WEBHOOK_MAX_ATTEMPTS=5`, `RETAIN_UPLOADS=false`
- `OTEL_EXPORTER_OTLP_ENDPOINT`, `LOG_LEVEL`

Mirror every variable in `.env.example`.

**0.4 Version constants.** In `src/talentgraph/__init__.py`, set `__version__ = "0.1.0"` and `PIPELINE_VERSION = "1"`.

**0.5 Core schemas skeleton.** Create `src/talentgraph/core/schemas/` with:
- `AgentMessage`, `AgentResult`, `AgentError` and `QualityScore` (plan §5)
- empty placeholder models `ParsedResume`, `SkillProfile` and `MatchResult`, each with `schema_version`
- `core/errors.py` with a `TalentGraphError` base class that has `code`, `http_status` and `retryable`

**0.6 LLM wrapper.** Create `src/talentgraph/llm/client.py` with an `LLMClient` protocol and `async def extract(schema: type[T], system: str, user: str) -> T`. The `GeminiLLM` implementation:
- uses the official `google-genai` SDK: `genai.Client(api_key=...)` and `client.aio.models.generate_content(model=..., contents=user, config=types.GenerateContentConfig(system_instruction=system, response_mime_type="application/json", response_schema=schema, temperature=0))`
- validates `response.text` with `schema.model_validate_json()`, and treats a validation failure as a retryable error (one retry), then as an `LLMError`
- reads the model and fallback model from settings, and switches to the fallback on 429 or exhausted daily quota
- applies a timeout and tenacity retries on 429, 5xx and connection errors
- acquires the shared Redis rate limiter (`llm/ratelimit.py`: RPM and RPD token bucket) and the per-process semaphore
- emits token and latency metrics from `usage_metadata` (stubbed for now)

Also create `llm/fake.py` with `FakeLLM`, which returns responses from a fixtures directory keyed by schema name and input hash, with an optional simulated latency for `stub` mode. A `get_llm()` factory returns `FakeLLM` when `LLM_MODE` is `fake` or `stub`, or when no `GEMINI_API_KEY` is set.

**0.7 Database layer.**
- `db/session.py`: async engine and session factory.
- `db/models.py`: all tables from plan §7.1.
- `alembic init migrations` (async template), followed by an initial migration.

**0.8 Embeddings layer.**
- `embeddings/encoder.py`: a process-wide singleton `Encoder` with `encode(list[str]) -> np.ndarray` and normalized vectors.
- `embeddings/vector_store.py`: a `VectorStore` protocol (`upsert`, `query(vector, k, where)`, `delete`) plus `ChromaVectorStore` and an in-memory `NumpyVectorStore` for tests.

**0.9 Minimal API.** `api/main.py` defines the FastAPI app with a lifespan that opens the DB, Redis, Chroma and encoder. It exposes `GET /health` (always 200) and `GET /ready`, which checks DB, Redis and Chroma and returns 200 or 503. Mount the routers under `/api/v1`.

**0.10 Containers.**
- **`Dockerfile`:** multi-stage, using a `uv sync --frozen` builder and a slim runtime. Pre-download the embedding model at build time so cold starts are fast.
- **`docker-compose.yml`:** services `api`, `worker` (Celery: `celery -A talentgraph.worker.celery_app worker`), `flower` (optional profile), `postgres:16`, `redis:7`, `chromadb/chroma`, `jaeger` and `prometheus`. Add healthchecks and named volumes, and have the api run `alembic upgrade head` on start.

**0.11 CI.** Create `.github/workflows/ci.yml`. It runs ruff, mypy and pytest (unit), and then a second job that starts compose and runs `pytest -m integration`.

**0.12 README.md.** Cover the quick start (compose up, then open `/docs`), the dev commands and links to the plan.

### Deliverables
- A skeleton repository that matches plan §11.
- A compose stack that comes up healthy.
- An initial Alembic migration.
- CI configuration.

### Exit criteria

| # | Check | How to verify | Pass condition |
|---|---|---|---|
| 0-A | Lint and types are clean | `uv run ruff check . && uv run ruff format --check . && uv run mypy src` | Exit code 0 |
| 0-B | Unit tests run offline | `uv run pytest` with networking disabled | ≥ 5 tests (settings, schemas, FakeLLM, NumpyVectorStore, errors); all pass |
| 0-C | The stack comes up | `docker compose up -d --build`, then `docker compose ps` | All services `healthy` within 120 s |
| 0-D | Liveness and readiness | `curl localhost:8000/health` and `curl localhost:8000/ready` | Both 200; `/ready` lists db, redis and chroma as `ok` |
| 0-E | Migrations apply cleanly | `docker compose exec api alembic upgrade head`, then `alembic downgrade base`, then `upgrade head` | No errors, and all tables from plan §7.1 exist |
| 0-F | OpenAPI is served | `GET /openapi.json` and `/docs` | 200 |
| 0-G | The LLM wrapper is safe | Unit test: `get_llm()` returns `FakeLLM` when there is no key; an integration test marked `llm` makes one real `extract()` call that returns a valid Pydantic object | Unit test passes (the `llm` test is optional when no key is available) |
| 0-H | CI is green | Push a branch (the owner does all commits and pushes) | Both CI jobs pass |
| 0-I | Celery worker works | `docker compose exec worker celery -A talentgraph.worker.celery_app inspect ping`. On Windows, run it natively with `uv run celery -A talentgraph.worker.celery_app worker --pool=solo` | Ping replies `pong`; the `talentgraph.ping` task returns `pong` |

---

## Phase 1: Data foundation (taxonomy & datasets)

**Goal:** the skill taxonomy loaded into Postgres and Chroma, plus every dataset and gold set needed to build and evaluate Phases 2–4.
**Depends on:** Phase 0.

### Steps

**1.1 Taxonomy sources.**
- Download ESCO (skills, skill hierarchy, alt-labels) and the O\*NET Technology Skills and Tools tables into `data/taxonomy/raw/`.
- Make `data/taxonomy/raw/` gitignored and give it a `download.py` that pins the source versions.
- Record the licenses in `data/taxonomy/ATTRIBUTION.md`.

**1.2 Build the 4-level tree** with `scripts/build_taxonomy.py`.
- Map the sources into **Domain → Category → Subcategory → Skill** (plan §6.2). Domains are `Technical Skills`, `Business Skills`, `Soft Skills` and `Domain Knowledge`, with industry sub-trees for the 10+ industries.
- Merge in the curated tech list `data/taxonomy/curated_tech.yaml`, which should have ≥ 1,500 entries covering languages, frameworks, cloud, data, ML/AI, DevOps, security, mobile, design tools and PM tools.
- Deduplicate by normalized name.
- Write `data/taxonomy/skills.csv` (`slug, name, type, level, parent_slug, description`).

**1.3 Aliases.**
- Generate `data/taxonomy/aliases.csv` (`slug, alias, source`) from:
  - the source alt-labels
  - curated abbreviations in `aliases_curated.yaml` (JS, TS, K8s, TF, GCP, AWS, ML, DL, NLP, CV, CI/CD, PM, UX, etc.)
  - punctuation and spacing variants (`react.js`, `react js`, `reactjs`)
  - LLM-proposed aliases, generated by the resumable generator (many skills per request, to save quota) and saved as `source=llm`
- Mark ambiguous aliases (`go`, `r`, `c`, `spring`, `swift`, `rust`, `excel` and similar) with `ambiguous=true`.
- Spot-check 200 random LLM aliases by hand, and record the error rate in the progress record.

**1.4 Implications and relations.**
- `data/taxonomy/implications.yaml`: at least 150 rules, such as the TensorFlow, PyTorch and Keras rule leading to Deep Learning.
- `relations.yaml`: at least 300 related or prerequisite edges, used for upskilling paths.

**1.5 Loader.** `scripts/seed.py --taxonomy` is an idempotent upsert into `skills`, `skill_aliases`, `skill_implications` and `skill_relations`. It sets `taxonomy_version` from the content hash, then embeds each skill (name, top 3 aliases and description) and upserts it into the Chroma `skills` collection.

**1.6 Ground-truth profiles.** `scripts/gen_profiles.py` generates **≥ 550** profiles as JSON that conforms to `ParsedResume`:
- ≥ 10 industries (software, data, finance, healthcare, marketing, design, manufacturing, education, sales, legal, operations)
- a seniority mix
- Faker for PII, and Gemini for realistic experience bullets. Use the **rate-limited, resumable** generator: it writes a checkpoint after each item to `data/.checkpoints/` and stops cleanly when the daily quota is reached, so you can rerun it the next day
- each profile's skills drawn from the taxonomy, with some deliberate alias and variant forms. The gold canonical IDs are kept in `*.gt.json`.
- ~5% made-up "emerging" skills, labeled as such

**1.7 Rendering.** `scripts/render_resumes.py` renders each profile with templates to PDF (ReportLab), DOCX (python-docx) and TXT.
- Templates: `single_column`, `two_column`, `sidebar`, `table_based`, `creative` (icons, text boxes, coloured headers) and `minimal_txt`, with ≥ 6 in total. Each profile is rendered with 1–2 templates.
- **Noise injection** with a seed: typos (1%), mixed date formats, missing sections (10%), reordered sections, and headers renamed with synonyms.
- Output goes to `data/resumes/{train,val,test}/` with a 70/15/15 split stratified by industry and template.

**1.8 Job descriptions.** `scripts/gen_jobs.py` produces ≥ 110 JDs across engineering, data science, PM, design and other families, each as `job_xxx.txt` plus a `job_xxx.gt.json` (`JobRequirements` with canonical skill IDs, importance and min_years).

**1.9 Normalization gold set.**
- Build `data/eval/normalization_gold.csv` with ≥ 1,000 rows of `raw, context, expected_slug | NEW`.
- About 70% are sampled from the profiles' alias forms. About 30% are hand-written hard cases: typos, versions, ambiguous terms with context, multi-skill strings, and unknown skills.
- Split it into val and test.

**1.10 Matching gold set.** `scripts/label_matches.py` handles this.
- For each job, select 20 candidates: 5 strong, 5 partial, 5 weak and 5 random, based on gold skill overlap so the grades vary.
- An LLM judge with a written rubric (`data/eval/match_rubric.md`) assigns a 0–4 relevance grade and a rationale. It uses the same resumable, rate-limited generator; about 2,000 calls may take several days of free quota, so start this step early, in parallel with 1.7–1.9.
- Export a `human_labeling.csv` sample of ≥ 200 pairs for human double-labeling. Compute Cohen's κ (weighted) once the human labels arrive.
- Split by job: 70/15/15.

**1.11 Data documentation.** `data/README.md` covers how to regenerate everything, dataset statistics (counts by industry, template, format and split), and the known limitations. Large binaries are regenerated by the scripts and not committed; commit only the JSON, CSV and YAML files, plus a small sample (~30 files) under `tests/fixtures/resumes/`.

### Deliverables
- The taxonomy CSV and YAML files, and the seed script.
- Seeded Postgres and Chroma.
- ≥ 500 rendered resumes with ground truth.
- ≥ 100 JDs.
- Both gold sets.
- `data/README.md`.

### Exit criteria

| # | Check | How to verify | Pass condition |
|---|---|---|---|
| 1-A | Taxonomy size | `uv run python scripts/seed.py --taxonomy --stats` | ≥ 5,000 skills, ≥ 15,000 aliases, 4 levels, every skill except the domain roots has a parent, no cycles |
| 1-B | Taxonomy integrity tests | `uv run pytest tests/unit/test_taxonomy_files.py` | Unique slugs and normalized aliases; every implication and relation references an existing slug; every ambiguous alias is flagged |
| 1-C | DB and vector parity | Integration test: count of `skills` rows == count of Chroma `skills` | Equal, and `taxonomy_version` matches |
| 1-D | Required examples resolve | Unit test with exact alias lookup | `js→javascript`, `k8s→kubernetes`, `react.js→react`, `ReactJS→react`, `ML Engineering→machine-learning-engineering` all resolve |
| 1-E | Resume corpus | `uv run python scripts/render_resumes.py --stats` | ≥ 500 resumes; ≥ 10 industries; ≥ 6 templates; both PDF and DOCX are each ≥ 40% of the corpus; every file has a `.gt.json` that validates against `ParsedResume` |
| 1-F | Job corpus | Stats script | ≥ 100 JDs covering engineering, data science, PM and design; every JD has a valid `JobRequirements` gt |
| 1-G | Gold sets | Stats script | Normalization gold ≥ 1,000 rows with ≥ 25% hard cases; match gold ≥ 2,000 pairs whose grade distribution has no grade above 40% |
| 1-H | Label quality | Progress record | LLM alias spot-check error ≤ 5%; human κ is reported, or marked "pending" with the CSV exported |
| 1-I | Reproducibility | Delete the generated dirs, then rerun the scripts with the same seed | Identical file hashes for the deterministic parts (rendering, splits) |

---

## Phase 2: Parsing Agent

**Goal:** a `ParsingAgent` that turns PDF, DOCX or TXT into a validated `ParsedResume` and meets M1 on the validation split. The design is in plan §6.1.
**Depends on:** Phases 0 and 1.

### Steps

**2.1 Final `ParsedResume` schema.** Write it in `core/schemas/resume.py` exactly as in plan §6.1, with per-field `confidence` and `source`. Add schema tests.

**2.2 Type detection.** `agents/parsing/detect.py` detects the type from magic bytes and enforces the size and page limits. It raises `UnsupportedFileType` (415), `FileTooLarge` (413) or `UnsupportedContent` (422, for scanned PDFs).

**2.3 LayoutDocument.** Write the `Block` and `LayoutDocument` models in `agents/parsing/layout.py`.

**2.4 PDF extractor** (`pdf.py`).
- Get spans with PyMuPDF and group them into blocks.
- Run column detection (plan §6.1), with seeded k-means and silhouette selection, and produce the reading order.
- Detect tables with pdfplumber and merge them in as table blocks.
- Detect scanned pages using the text-area ratio.
- Add unit tests on fixture PDFs for one, two and sidebar columns, a table, and a scanned page.

**2.5 DOCX extractor** (`docx.py`). Read paragraphs and tables in body order, text boxes through `w:txbxContent`, and headers and footers. Use heading styles to set `font_size` and `bold` hints.

**2.6 TXT extractor** (`text.py`). Detect the encoding (UTF-8, falling back to cp1252), split into paragraphs, and add header hints.

**2.7 Section detector** (`sections.py`).
- Load the lexicon from `config/section_lexicon.yaml` (≥ 150 header variants).
- Score candidate headers with lexicon, typography and position signals.
- Assign each block to the nearest header above it in reading order.
- For blocks with no header, use a TF-IDF plus logistic-regression classifier trained on the train split by `scripts/train_section_clf.py`. Save the model to `models/section_clf.joblib`; it is regenerated by the script and not committed if large.

**2.8 Rule extractors** (`rules.py`):
- email
- phone (`phonenumbers`, E.164 output)
- URLs, classified as LinkedIn, GitHub or other
- date ranges: `Jan 2020 – Present`, `2019-21`, `03/2018 to 06/2020` and `Summer 2017`, normalized to `YYYY-MM` with an `is_current` flag
- location (gazetteer in `data/gazetteer.csv`)
- skill candidates by n-gram lookup against the alias index

Each extractor has ≥ 10 table-driven unit tests.

**2.9 LLM extraction** (`llm_extract.py`).
- The prompt lives in `llm/prompts/resume_extraction.md`. It is a static system prompt that holds the schema guidance and few-shot hints. Field guidance must be in the prompt text, because `response_schema` can drop nested field descriptions.
- The user message is the section-labeled text in reading order plus the rule hints.
- Output is a `ResumeExtraction` (Pydantic) that has `evidence` per entity.
- Record a FakeLLM fixture for every file in `tests/fixtures/resumes/`, generated once with the real Gemini model by `scripts/record_llm_fixtures.py`.

**2.10 Merge and validate** (`agent.py`).
- Apply the precedence rules from plan §6.1.
- Fix date ordering and compute `duration_months`.
- Detect the layout class.
- Compute the quality score.
- Without the LLM (disabled or failed after retries), return a rules-only result with `status=partial`.

**2.11 Parsing eval** (`eval/parsing.py`). Implement field-level P/R/F1 (plan §10.2), with Hungarian alignment for list entities, breakdowns by field, template and format, and a Markdown report.

**2.12 Iterate.** Run the eval on **val** and fix the worst-performing fields and templates until the targets are met. Log each iteration's scores in the progress record.

### Deliverables
- `agents/parsing/*` with tests.
- The section classifier.
- The LLM prompt and fixtures.
- `eval/parsing.py`.
- `reports/parsing_val_<sha>.md`.

### Exit criteria

| # | Check | How to verify | Pass condition |
|---|---|---|---|
| 2-A | Unit tests | `uv run pytest tests/unit/parsing` | All pass; ≥ 80% line coverage on `agents/parsing` |
| 2-B | Format coverage | Fixture tests | Every fixture PDF, DOCX and TXT, across all 6 templates, parses to a schema-valid `ParsedResume` |
| 2-C | **Accuracy (M1) on val** | `uv run python -m eval.parsing --split val` (real LLM, or recorded fixtures if available) | Overall micro F1 **≥ 0.85**; name, email and phone each **≥ 0.95**; no template below 0.75 |
| 2-D | Degradation | `uv run python -m eval.parsing --split val --no-llm` | Runs without errors and every result is `status=partial`; the F1 is recorded as a baseline (no threshold) |
| 2-E | Error handling | Unit tests | PNG → `UnsupportedFileType`; an 11 MB file → `FileTooLarge`; a scanned PDF → `UnsupportedContent`; a corrupt PDF → `UnsupportedContent`, not a crash |
| 2-F | Latency (agent only) | `uv run python -m eval.latency --agent parser --n 30` | p95 **≤ 6 s** with the real LLM; ≤ 0.5 s for the rules path |
| 2-G | Single LLM call | Unit test that counts FakeLLM calls | Exactly 1 extraction call per resume |

---

## Phase 3: Skill Taxonomy & Normalization Agent

**Goal:** a `NormalizationAgent` that maps raw skills to canonical IDs, infers hierarchy, estimates proficiency, and queues emerging skills. It must meet M2. The design is in plan §6.2.
**Depends on:** Phases 1 and 2.

### Steps

**3.1 Schemas.** Define the `SkillProfile` and `CandidateSkill` models (`skill_id`, `slug`, `name`, `path[]`, `proficiency 1–5`, `years`, `confidence`, `inferred`, `evidence[]`, `method: exact|fuzzy|embedding|llm|inferred`) and `EmergingSkillCandidate`.

**3.2 Cleaning** (`clean.py`). Lowercase, strip version numbers, unify punctuation, expand `C++`, `C#` and `.NET` safely, and split compound strings (`AWS/GCP`, `HTML, CSS & JS`). Write ≥ 30 table-driven tests.

**3.3 Taxonomy repository** (`db/repositories/taxonomy.py`) provides:
- an in-memory alias index loaded at startup and rebuilt when `taxonomy_version` changes
- `ancestors(id)`, `children(id)`, `related(id)`, `siblings(id)` and the implication rules
- **(after 3.3)**: a `TaxonomyCache` singleton

**3.4 Cascade** (`cascade.py`). Implement steps 1–5 of plan §6.2 with the thresholds in `config/normalization.yaml`. Ambiguous aliases always go to step 4 when there is context. Step 4 is **one batched LLM call per resume**: the schema is `list[{raw, chosen_slug | "NEW", confidence}]` and the prompt is `llm/prompts/skill_disambiguation.md`.

**3.5 Hierarchy inference** (`hierarchy.py`). Apply the implication rules and add ancestors with decayed confidence (`inferred=true`). Keep explicit and inferred skills separate in the output.

**3.6 Proficiency** (`proficiency.py`).
- Compute the feature extraction and scoring from plan §6.2, with weights in `config/proficiency.yaml`.
- Merge overlapping role intervals before counting years.
- Return the level, the years and a one-line `explanation`.

**3.7 Emerging skills** (`emerging.py`). Upsert into `emerging_skills` (occurrences +1, store up to 5 contexts). Report `is_review_ready` once `occurrences ≥ 3`. Add a repository function to approve (create a skill under a parent and re-embed), merge (add an alias) or reject. The API wiring comes in Phase 6.

**3.8 Agent** (`agent.py`). Takes a `ParsedResume` and returns a `SkillProfile`. Collect skills from the skills section, `skills_mentioned` in experience, project technologies and certifications. Deduplicate by `skill_id`, keeping the strongest evidence. The quality score follows plan §5.

**3.9 Normalization eval** (`eval/normalization.py`). Run it on the gold val set. Report precision, recall, per-method share, emerging precision (gold `NEW` rows correctly flagged) and the 25 worst confusions.

**3.10 Proficiency sanity set.** Hand-label 50 (skill, resume) pairs from val with a level from 1 to 5, in `data/eval/proficiency_gold.csv`. Tune `proficiency.yaml` against it.

**3.11 Iterate** on val until the targets are met.

### Deliverables
- `agents/normalization/*`.
- The config YAMLs.
- The prompts and fixtures.
- The eval script and report.
- The proficiency gold set.

### Exit criteria

| # | Check | How to verify | Pass condition |
|---|---|---|---|
| 3-A | Unit tests | `uv run pytest tests/unit/normalization` | All pass; ≥ 80% coverage |
| 3-B | Brief examples | Unit test | `JS→JavaScript`, `K8s→Kubernetes`, `React.js`/`ReactJS`/`React`→`React`, `ML Engineering`→`Machine Learning Engineering`; `{TensorFlow, PyTorch}` produces an inferred `Deep Learning` |
| 3-C | **Precision (M2) on val** | `uv run python -m eval.normalization --split val` | Precision **≥ 0.90**, recall **≥ 0.85** |
| 3-D | Ambiguity | Subset of gold rows tagged `ambiguous` | Accuracy ≥ 0.80 (for example, "Go" in a backend context maps to Go-lang, and "Go" as in "go-to-market" does not) |
| 3-E | Emerging detection | Gold `NEW` rows | ≥ 0.80 of them are flagged as emerging; ≤ 5% of known skills are wrongly flagged |
| 3-F | Proficiency | `eval/normalization.py --proficiency` | Exact-or-adjacent level agreement ≥ 0.80 on the 50-pair set; "5 years of Python" scores higher than "familiar with Python" (unit test) |
| 3-G | Cost and latency | Unit test plus latency script | ≤ 1 LLM call per resume; p95 normalization latency ≤ 1.5 s with the LLM and ≤ 0.3 s without |
| 3-H | Degradation | With the LLM disabled | Unresolved skills are queued as emerging candidates with `method=unresolved`, the agent returns `status=partial`, and nothing crashes |

---

## Phase 4: Semantic Skill-to-Job Matching Agent

**Goal:** a `MatchingAgent` that produces explainable scores, gap analysis and upskilling paths, tuned to meet M3. The design is in plan §6.3.
**Depends on:** Phases 1 and 3.

### Steps

**4.1 Schemas.** Define these models:
- `JobRequirements`: `title`, `role_family`, `seniority`, `required[]` and `nice_to_have[]` (each `{skill_id, importance 1–5, min_years?}`), and `education`
- `MatchRequest`
- `MatchResult`: `score`, `is_match`, `threshold`, `components{skill, experience, semantic, penalty}`, `breakdown[]`, `gaps[]`, `upskilling[]` and `explanation`

**4.2 Job parser** (`job_parser.py`). Structured LLM extraction using the prompt `llm/prompts/job_extraction.md`. Normalize the skills with the Normalization Agent, cache the result by text hash in Redis, and persist it to `jobs`. A structured `job` input skips the LLM.

**4.3 Scoring** (`scoring.py`). Implement plan §6.3 steps 2–6 as pure functions with weights from `config/matching.yaml`. Embedding similarity uses the cached skill vectors from Chroma, loaded into an in-memory matrix for speed.

**4.4 Thresholds** (`thresholds.py`). Accept a threshold value or a preset (`precision`, `balanced` or `recall`), and validate that the value is in [0, 1].

**4.5 Gap analysis and upskilling** (`gaps.py`). Implement plan §6.3 step 8. Each gap item is `{skill, required_level, current_level|null, importance, suggestions:[{skill, via: adjacent|prerequisite, effort: S|M|L}]}`.

**4.6 Agent** (`agent.py`). Takes `(SkillProfile, ParsedResume, JobRequirements)` and returns a `MatchResult` with the full breakdown. Also add a `rank(candidates, job)` helper for evaluation and `/match/rank`.

**4.7 Matching eval** (`eval/matching.py`). For each job in a split, rank its 20 labeled candidates. Compute NDCG@5 and @10 (gain = 2^grade − 1), Spearman ρ and Kendall τ against the gold grades, and the precision/recall at each preset (relevant means grade ≥ 3).

**4.8 Tune.** Use `scripts/tune_matching.py` to grid-search or Bayesian-optimize α, β, γ, λ_nice, the similarity floor and the penalty on the **train** split, maximizing mean NDCG@10. Write the best values to `config/matching.yaml`. Then calibrate the preset thresholds on **val** so that `precision` gives P ≥ 0.85, `recall` gives R ≥ 0.90, and `balanced` maximizes F1.

**4.9 Baselines for the report.** Measure two simpler matchers on the same split, to show the semantic approach adds value:
- (a) exact keyword overlap (Jaccard)
- (b) embedding similarity of the whole JD and whole resume alone

### Deliverables
- `agents/matching/*`.
- The tuned `config/matching.yaml`.
- `eval/matching.py`.
- A tuning log.
- A val report comparing the matcher against the baselines.

### Exit criteria

| # | Check | How to verify | Pass condition |
|---|---|---|---|
| 4-A | Unit tests | `uv run pytest tests/unit/matching` | All pass; ≥ 80% coverage; scoring functions tested on hand-calculated examples |
| 4-B | **Quality (M3) on val** | `uv run python -m eval.matching --split val` | Mean NDCG@10 **≥ 0.80**; Spearman ρ **≥ 0.60** |
| 4-C | Beats baselines | Same report | NDCG@10 is ≥ 0.05 above both baselines |
| 4-D | Semantics | Unit tests | A candidate with `ReactJS` fully satisfies a `React` requirement; `PyTorch` gives ≥ 0.9 credit toward `Deep Learning`; a missing required skill with importance 5 lowers the score and appears in `gaps` |
| 4-E | Threshold behaviour | Unit test plus the val report | The presets order as precision > balanced > recall; precision preset P ≥ 0.85 and recall preset R ≥ 0.90 on val |
| 4-F | Explainability | Schema test | Every requirement appears in `breakdown` with a `matched_skill`, `similarity_type`, `depth` and `credit`; the credits recompute to `components.skill` within 1e-6 |
| 4-G | Upskilling | Unit test | A candidate who has Docker but lacks Kubernetes gets a Kubernetes gap that suggests `via: adjacent` from Docker |
| 4-H | Latency | Latency script | Match with a cached JD: p95 ≤ 300 ms; with a new JD (LLM): p95 ≤ 6 s |

---

## Phase 5: Multi-Agent Orchestration Layer

**Goal:** a LangGraph pipeline that connects the three agents through the shared message protocol, with lifecycle management, retries, graceful degradation and traces. The design is in plan §4.2–4.4 and §6.4.
**Depends on:** Phases 2, 3 and 4.

### Steps

**5.1 Agent base** (`agents/base.py`).
- An `Agent` protocol with `name`, `startup()`, `shutdown()` and `async handle(msg: AgentMessage) -> AgentResult`.
- An `AgentRegistry` that holds the agents.
- `run_agent(agent, msg, *, timeout, retries)`. It wraps tenacity (retrying only on `retryable` errors), enforces `asyncio.timeout`, records an `AgentRun` per attempt, opens an OTel span (no-op until Phase 8), and converts exceptions into `AgentError`.

**5.2 Adapt the three agents** to the `Agent` protocol. Their payloads must be the Phase 2–4 schemas.

**5.3 State and graph** (`orchestrator/state.py`, `graph.py`). Build `PipelineState` and the graph in plan §4.2, with conditional edges for degradation and a final `status` computation. Expose two entry points:
- `run_parse_pipeline(file, opts)`, which runs parse, then normalize, then persist
- `run_match_pipeline(candidate_id, job, opts)`, which loads the profile, then matches, then persists

**5.4 Persistence node.** Writes `candidates`, `candidate_skills`, `matches` and `agent_runs` in a single transaction, and is idempotent by `file_sha256 + api_key + pipeline_version`.

**5.5 Caching.** Check the parse-result cache before the parse node (plan §4.4). On a cache hit, skip to the end with `meta.cache: "hit"`.

**5.6 CPU offload and lifecycle.**
- Run PDF layout analysis and embedding in a bounded thread pool.
- Wire the registry `startup()` and `shutdown()` calls into the FastAPI lifespan and the Celery `worker_process_init` and `worker_process_shutdown` signals.

**5.7 Fault-injection harness.** Add `tests/integration/test_degradation.py` with a `FaultInjector` that makes an agent raise, time out, or fail N times then succeed.

**5.8 Concurrency test.** `tests/integration/test_concurrency.py` runs 50 pipelines concurrently with FakeLLM and checks that results don't get mixed up, that DB rows are correct, and that nothing deadlocks.

### Deliverables
- `orchestrator/*` and `agents/base.py`.
- The integration tests.
- A graph diagram exported to `docs/architecture.md` (Mermaid, from `graph.get_graph().draw_mermaid()`).

### Exit criteria

| # | Check | How to verify | Pass condition |
|---|---|---|---|
| 5-A | Happy path | Integration test | Parse, then normalize, produces `status=ok` with rows persisted; the match pipeline produces `status=ok` |
| 5-B | **Graceful degradation** | `pytest tests/integration/test_degradation.py` | Matcher fails → `partial` with the profile kept. Normalizer fails → `partial` with raw skills kept. LLM fails → rules-only `partial`. Parser fails completely → `failed` with a structured error. In every case the result includes `errors[]` |
| 5-C | Retry | Same file | "Fail 2× then succeed" gives `ok` with 3 `AgentRun` attempts recorded; a non-retryable error is not retried |
| 5-D | Timeouts | Same file | A hanging agent is cut off at its timeout, and the pipeline returns within timeout + 1 s |
| 5-E | Message protocol | Unit test | Every inter-agent hop is an `AgentMessage` with the same `trace_id` and correct `parent_id` chain; payloads validate against the schemas |
| 5-F | Concurrency | `pytest tests/integration/test_concurrency.py` | 50/50 succeed; no cross-contamination; no unhandled warnings |
| 5-G | Cache | Integration test | A second parse of the same file returns `cache: hit` in under 200 ms |
| 5-H | Traces recorded | Integration test | `agent_runs` has one row per agent attempt, with latency and quality |

---

## Phase 6: Core REST API (sync endpoints, auth, rate limiting, errors)

**Goal:** a production-grade FastAPI layer covering every synchronous endpoint in plan §8, with API keys, rate limits, validation and RFC 7807 errors.
**Depends on:** Phase 5.

### Steps

**6.1 Problem details** (`api/problems.py`).
- Exception handlers map `TalentGraphError`, `RequestValidationError`, `HTTPException` and unhandled exceptions to `application/problem+json`, including `trace_id`.
- Write `docs/errors.md`, listing every error `type` with its status code and a remedy.

**6.2 API keys** (`api/auth.py`, `scripts/create_api_key.py`).
- The key format is `tg_live_…`. Store only the SHA-256 hash and the prefix.
- A `require_scope("parse")` dependency enforces scopes.
- Update `last_used_at` asynchronously.
- The CLI prints a new key once.

**6.3 Rate limiting** (`api/ratelimit.py`).
- A Redis sliding-window log, implemented as an atomic Lua script, per key.
- Add the `X-RateLimit-*` headers to every response, and return `429` with `Retry-After` when a key is over its limit.

**6.4 Upload validation.** Check the multipart size limit while streaming (reject before reading the whole body where possible), check magic bytes, and map violations to 413 or 415.

**6.5 Routers.** Build these:
- `routers/parse.py`: `POST /parse`, which accepts `?include=trace`.
- `routers/candidates.py`: `GET /candidates/{id}` and `GET /candidates/{id}/skills`, with filters. Ownership is enforced, so another key's candidate returns 404.
- `routers/match.py`: `POST /match`, with an optional `POST /match/rank`.
- `routers/skills.py`: `GET /skills/taxonomy` (tree browse, `parent_id`, `depth`, cursor pagination), `GET /skills/search?q=` (alias, fuzzy and semantic search, merged and ranked), `GET /skills/{id}`, and the admin endpoints `GET /skills/emerging` and `POST /skills/emerging/{id}/review`.

**6.6 Response envelope and OpenAPI polish.**
- Pipeline endpoints use the `{data, meta}` envelope.
- Every route has a summary, a description, examples (`openapi_examples`), response models for its error codes, tags and an `X-API-Key` security scheme.

**6.7 Idempotency** (`api/idempotency.py`). Cache responses for an `Idempotency-Key` in Redis for 24 hours. If the same key arrives with a different body, return 422.

**6.8 E2E tests** (`tests/e2e/`). Use `httpx.AsyncClient` against the compose stack with FakeLLM. Cover the happy path, the error paths and the auth paths for every route.

### Deliverables
- `api/*`.
- `docs/errors.md`.
- The key CLI.
- The e2e tests.
- A polished OpenAPI spec exported to `docs/openapi.json`.

### Exit criteria

| # | Check | How to verify | Pass condition |
|---|---|---|---|
| 6-A | Endpoint coverage | `uv run python -m eval.api_contract` | Every sync endpoint in plan §8 exists, with the right methods and response models |
| 6-B | OpenAPI quality | `openapi-spec-validator docs/openapi.json` and `npx @stoplight/spectral-cli lint docs/openapi.json` | 0 errors; every operation has a summary, a description, ≥ 1 example and documented 4xx responses |
| 6-C | Auth | E2E tests | No key → 401; bad key → 401; missing scope → 403; another key's candidate → 404; `/health` works without a key |
| 6-D | Rate limit | E2E test with a key limited to 5/min | The 6th request gets 429 with `Retry-After`; the headers are correct; the window recovers |
| 6-E | Validation and errors | E2E tests | Unsupported type → 415; too large → 413; bad JSON → 422 with field errors; all errors are `application/problem+json` with `trace_id` |
| 6-F | Brief workflow | E2E test | Parse a resume, get `candidate_id`, `GET /candidates/{id}/skills`, `POST /match` with a JD, get a score and gaps |
| 6-G | Taxonomy browsing | E2E tests | Tree paging works; `search?q=k8s` returns Kubernetes first; `search?q=deep lerning` (typo) returns Deep Learning in the top 3 |
| 6-H | Emerging review | E2E test | An admin approves an emerging skill, which then appears in the taxonomy; a parse of a resume containing it maps it via `exact` |
| 6-I | Sync latency (M6 preview) | `uv run python -m eval.latency --endpoint parse --n 30` against compose with the real LLM | p95 **< 10 s** |

---

## Phase 7: Async batch processing & webhooks

**Goal:** bulk uploads processed by Celery workers, with job tracking and signed, retried webhooks.
**Depends on:** Phase 6.

### Steps

**7.1 Batch submission** (`routers/batch.py`). `POST /parse/batch` accepts multipart with up to `MAX_BATCH_FILES` files, or one ZIP that is safely extracted with zip-slip and zip-bomb guards. It also takes an optional `callback_url` (https only, with private-IP SSRF protection) and `Idempotency-Key`.
- The endpoint stores the files in a shared volume or Postgres large objects. The choice is recorded as an ADR; the default is a shared Docker volume `uploads/`.
- It creates the `batch_jobs` and `batch_items` rows, enqueues one Celery task per item (`parse_item.delay(item_id)`) after the DB transaction commits, and returns `202` with `{batch_job_id, status_url}`.

**7.2 Worker** (`worker/celery_app.py`, `worker/tasks.py`).
- Celery config: Redis broker; `task_acks_late=True`; `task_reject_on_worker_lost=True`; `worker_prefetch_multiplier=1`; `task_time_limit=90` and `task_soft_time_limit=60`; JSON serializer only; separate queues `parse` and `webhooks`.
- `parse_item(item_id)` is a sync task that runs `asyncio.run(run_parse_pipeline(...))`. It has `autoretry_for` infrastructure errors (DB, Redis, Chroma), `retry_backoff=True` and `max_retries=3`.
- Each task updates its `batch_item`, increments the job counters atomically (a single `UPDATE … RETURNING`), and deletes the upload unless `RETAIN_UPLOADS` is set.
- The task that moves the job to its last item computes the final status and enqueues `deliver_webhook` on the `webhooks` queue.
- The DB engine, the encoder and the agent registry are set up per worker process in `worker_process_init`. Don't share async engines across a fork.
- Tasks must be idempotent: skip an item that is already in a terminal state, because `acks_late` can redeliver it.

**7.3 Status endpoints.**
- `GET /jobs/{id}` returns status, counts, `progress %` and timestamps.
- `GET /jobs/{id}/results` returns paginated items with `candidate_id`, status and error.

**7.4 Webhooks** (`api/webhooks.py` plus a worker task).
- The payload follows plan §8.1, signed with HMAC-SHA256 using the per-key secret.
- Delivery is a Celery task with `self.retry(countdown=backoff(attempt))`, up to 5 attempts. Any 2xx counts as delivered.
- Every attempt is logged in `webhook_deliveries`.
- Add `POST /webhooks/test`, which sends a test event to a URL.

**7.5 Webhook receiver example and verifier.**
- `examples/webhook_receiver_fastapi.py`.
- A verifier function in the Python SDK (Phase 9), with its unit tests written now.

**7.6 Fairness.** Each API key is limited to N items in flight across all workers (`MAX_INFLIGHT_PER_KEY`), so one tenant can't starve the others.

### Deliverables
- The batch router, the worker tasks, the webhook delivery code and its tests.
- An ADR on upload storage.

### Exit criteria

| # | Check | How to verify | Pass condition |
|---|---|---|---|
| 7-A | Batch happy path | E2E test: upload 20 files with `callback_url` pointing at a test receiver | `202` immediately (< 1 s); the job reaches `completed`; 20 results; the webhook arrives once with a valid signature |
| 7-B | Mixed results | E2E test: 18 good, 1 corrupt, 1 forced partial | Status `completed_with_errors`; counts `succeeded=18, failed=1, partial=1`; per-item errors are present |
| 7-C | Webhook retry | E2E test: the receiver returns 500 twice, then 200 | Delivered on attempt 3; 3 rows in `webhook_deliveries`; the backoff timing is within tolerance |
| 7-D | Signature | Unit test | Verification succeeds with the right secret and fails when the body or timestamp is tampered with or the timestamp is more than 5 minutes old |
| 7-E | Security | Unit and e2e tests | Zip-slip path, zip bomb, `http://` callback and `http://169.254.169.254` callback are all rejected with a 4xx problem response |
| 7-F | Scale-out | `docker compose up -d --scale worker=3`, then submit 100 files with `LLM_MODE=stub` | All complete; no item is processed twice (check the logs and DB); throughput is above that of 1 worker |
| 7-G | Worker crash recovery | `docker kill` a worker mid-batch | Its unacknowledged items are redelivered (`acks_late`) and processed exactly once (idempotency check); the job still completes |
| 7-H | 100-resume batch timing | Stopwatch test, 3 workers, `LLM_MODE=stub` with `LLM_STUB_LATENCY_MS` set to the measured real p50 | Completes in under 3 min; record the actual time. Note: with the real free tier, throughput is capped by `LLM_RPM_LIMIT`; record that number too |

---

## Phase 8: Observability

**Goal:** per-agent execution traces, latency metrics and quality scores that operators and API consumers can see.
**Depends on:** Phases 5–7.

### Steps

**8.1 Logging** (`observability/logging.py`).
- structlog JSON output.
- Contextvars bind `trace_id`, `api_key_prefix` and `agent` per request or task.
- PII scrubbing: a processor redacts email and phone patterns from messages.

**8.2 Tracing** (`observability/tracing.py`).
- OTel tracer provider exporting over OTLP to Jaeger, plus FastAPI auto-instrumentation.
- `run_agent()` spans with attributes `agent`, `attempt`, `status` and `quality`.
- Child spans for LLM calls (model, tokens in and out, cache read tokens), embedding calls and DB calls.
- Trace context is propagated into Celery tasks by `opentelemetry-instrumentation-celery` (through the message headers), and the `AgentMessage.trace_id` keeps the same value.

**8.3 Metrics** (`observability/metrics.py`). Add every metric in plan §9 and expose `/metrics`. Exclude `/metrics` from the public OpenAPI and protect it with network-level access only.

**8.4 Per-request trace.** `?include=trace` on `/parse` and `/match` returns an agent timeline (`agent`, `attempts`, `latency_ms`, `quality`, `status`, `error_code`) built from the in-memory `agent_runs`.

**8.5 Dashboards (optional but recommended).** Configure the Prometheus scrape in `deploy/prometheus.yml`. Provide a Grafana dashboard JSON in `deploy/grafana/` with these panels:
- agent p50 and p95 latency
- runs by status
- quality histograms
- LLM tokens and cost estimate
- queue depth (Celery queue length in Redis), and an optional link to Flower
- emerging skills pending

**8.6 Runbook** (`docs/runbook.md`). Cover how to find a slow request by `trace_id`, what each alert means, and how to scale workers.

### Exit criteria

| # | Check | How to verify | Pass condition |
|---|---|---|---|
| 8-A | End-to-end trace | Parse one resume, then open Jaeger | One trace with a root HTTP span and child spans for parser, normalizer, LLM call, embedding and persist; the `trace_id` equals `meta.trace_id` |
| 8-B | Async trace continuity | Batch of 3 | Each worker task's spans link to the submitting request's trace |
| 8-C | Metrics exposed | `curl localhost:8000/metrics` after traffic | Every metric in plan §9 is present with non-zero samples, and the latency histograms have per-agent labels |
| 8-D | Per-request timeline | `POST /parse?include=trace` | `meta.trace` lists all agents with latency, attempts and quality |
| 8-E | Degradation visible | Fault-injected run | `tg_agent_runs_total{status="failed"}` increments; the span is marked error; the log line has `error_code` |
| 8-F | No PII in logs | Unit test: run the pipeline on a fixture, capture logs, grep for the fixture's email, phone and name | 0 occurrences |
| 8-G | Overhead | Latency script with tracing on vs. off | p50 overhead ≤ 5% |

---

## Phase 9: SDKs, examples & documentation

**Goal:** third parties can integrate within minutes, using the Python or JS SDK or plain cURL.
**Depends on:** Phase 7 (a stable OpenAPI spec), with Phase 8 nice to have.

### Steps

**9.1 Freeze API v1.** Export `docs/openapi.json` and add a CI check that fails if the exported spec differs from the committed one without a version note.

**9.2 Python SDK** (`sdks/python/`). The `talentgraph` package has:
- `TalentGraph(api_key, base_url)` and `AsyncTalentGraph`
- the methods `parse(file)`, `parse_batch(files, callback_url)`, `get_job(id)`, `wait_for_batch(id, timeout)`, `iter_batch_results(id)`, `get_candidate(id)`, `get_skills(id, **filters)`, `match(candidate_id, job, threshold|preset)`, `taxonomy(parent_id, depth)`, `search_skills(q)` and `verify_webhook(payload, header, secret)`
- typed models generated from OpenAPI
- retries on 429 and 5xx that honour `Retry-After`
- typed exceptions mapped from problem types

Its tests use `respx` mocks, plus one integration test against compose.

**9.3 JS/TS SDK** (`sdks/js/`).
- The `@talentgraph/sdk` package uses `openapi-typescript` types and `fetch`, and offers the same methods, a `verifyWebhook` helper and retries.
- Builds ESM and CJS through `tsup`.
- Tests use `vitest` with `msw` mocks.
- Runs on Node 18+.

**9.4 Examples** (`examples/`):
- `curl.md`, a full walkthrough
- `python/quickstart.py`, `python/batch_with_webhook.py`, `python/rank_candidates.py`
- `js/quickstart.mjs`, `js/batch_with_webhook.mjs`
- `webhook_receiver_fastapi.py` and `webhook_receiver_express.mjs`

**9.5 Documentation** (`docs/`):
- `getting-started.md`: get a key, then make your first parse, then your first match, in 5 minutes.
- `api-guide.md`: concepts, envelopes, pagination, idempotency, rate limits, webhooks, partial results and versioning.
- `architecture.md`: diagrams from plan §4 plus the exported graph.
- `taxonomy.md`: structure, how to browse and search, and the emerging-skill workflow.
- `matching.md`: how scores are computed, what the presets mean, and how to read the breakdown and gaps.
- Update the top-level `README.md`.

### Exit criteria

| # | Check | How to verify | Pass condition |
|---|---|---|---|
| 9-A | Python SDK | `cd sdks/python && uv run pytest` | All pass; there is a method for every endpoint in plan §8 |
| 9-B | JS SDK | `cd sdks/js && npm ci && npm test && npm run build` | All pass; types compile under `strict` |
| 9-C | Examples run | `scripts/run_examples.sh` against compose (FakeLLM) | Every example exits 0 with the expected output |
| 9-D | Webhook verifiers agree | Cross-test: sign in Python, verify in JS and vice versa | Both directions succeed |
| 9-E | Docs completeness | Checklist in the progress record | Every endpoint, error type, header, preset and webhook event is documented; all doc links resolve (`lychee docs/`) |
| 9-F | Fresh-user test | A new agent or person follows `getting-started.md` from a clean clone | Reaches a successful match in ≤ 15 minutes, without help; note any friction found |

---

## Phase 10: System evaluation & hardening

**Goal:** measure every evaluation criterion from `idea.md` on the **held-out test split** under realistic conditions, fix bottlenecks, and publish the final evaluation report.
**Depends on:** Phases 2–9.

### Steps

**10.1 Freeze the configs.** Tag the commit `eval-candidate-1`. After that, make no tuning changes based on test results. If a fix is needed, go back to val, re-tag, and note it in the report.

**10.2 Accuracy evals on the test split.** Run parsing (M1), normalization (M2) and matching (M3) with the real LLM, and keep the reports.

**10.3 API completeness (M4).** Run `eval.api_contract` plus the e2e suite and the OpenAPI lint.

**10.4 Load test (M5).** Run the stack with `LLM_MODE=stub` and `LLM_STUB_LATENCY_MS` set to the real p50 measured in 10.5. The free tier can't sustain this load (plan D10). In `eval/load/locustfile.py`, the user mix is:

| Share | Request |
|---|---|
| 50% | `POST /parse` (single) |
| 25% | `POST /match` |
| 15% | taxonomy browse and search |
| 10% | `POST /parse/batch` (10 files) |

Ramp to **50 concurrent users** over 2 minutes, hold for 10 minutes, with 3 workers. Record the success rate, latency percentiles per endpoint, and error types.

**10.5 Latency (M6).** Run `eval/latency.py` with the **real Gemini API**, doing 50 sequential single parses, paced to stay under `LLM_RPM_LIMIT`, on test-split files (a mix of formats, cold cache) and break the result down per agent.

**10.6 Chaos checks.** During the load test, run each of these for 60 seconds:
- (a) block LLM egress, or switch to an invalid key, so the system sees LLM errors (simulates a quota or outage)
- (b) restart Redis
- (c) kill one worker

Record the behaviour. Partial results are expected; total failures are not.

**10.7 Fix and re-measure.** Profile the hot paths (`py-spy`) and fix the bottlenecks, for example by batching embeddings, pooling connections, or tuning the LLM concurrency semaphore. Re-run 10.4 and 10.5.

**10.8 Security review.** Check:
- dependency audit (`uv run pip-audit`)
- secret scan (`gitleaks`)
- container scan (`trivy image`)
- review of the auth, upload, ZIP and webhook SSRF paths

Fix all high and critical findings.

**10.9 Final report** (`reports/final/EVALUATION.md`). Give a table with the M1–M6 targets vs. actual results, the methodology, dataset statistics, baselines, ablations (no LLM, no embeddings step, no hierarchy inference), the chaos results, known limitations (synthetic data, LLM-judge labels, κ), and the next steps.

### Exit criteria

| # | Check | Pass condition |
|---|---|---|
| 10-A | **M1 parsing (test)** | Micro F1 ≥ 0.85; name, email and phone ≥ 0.95 |
| 10-B | **M2 normalization (test)** | Precision ≥ 0.90; recall ≥ 0.85 |
| 10-C | **M3 matching (test)** | NDCG@10 ≥ 0.80; Spearman ρ ≥ 0.60; beats both baselines |
| 10-D | **M4 API** | 100% endpoint coverage; 0 OpenAPI lint errors; e2e suite green |
| 10-E | **M5 reliability** | ≥ 99% success (2xx including partial) at 50 concurrent users for 10 minutes (stub LLM); 0 unhandled 5xx traces |
| 10-F | **M6 latency** | Single parse p95 < 10 s and p50 < 5 s (cold cache, real Gemini, sequential) |
| 10-G | Chaos | LLM outage gives partial results, not failures; a Redis restart recovers within 30 s; a killed worker loses 0 items |
| 10-H | Security | 0 high or critical findings open; gitleaks clean |
| 10-I | Report | `EVALUATION.md` is complete, links the raw JSON reports, and every number in it can be reproduced with the listed commands |

---

## Phase 11: Release & stretch goals

**Goal:** a tagged, reproducible v1.0 release, plus optional enhancements chosen by priority.
**Depends on:** Phase 10.

### Steps (release)

**11.1** Version bump to `1.0.0`, `CHANGELOG.md`, and a git tag `v1.0.0`. Build and push the images (if a registry is configured), or document `docker compose build`.

**11.2** Add a production compose override, `docker-compose.prod.yml`. It includes:
- no bind mounts
- resource limits
- `uvicorn --workers N`
- secrets loaded through env files
- Postgres backups through a cron sidecar

**11.3** Write the demo script `scripts/demo.sh`. It seeds the data, creates a key, parses 5 resumes, matches them against 2 JDs and prints the ranked results.

**11.4** Final pass: update `CLAUDE.md`, `README.md` and the status tracker.

### Stretch goals (each becomes a mini-phase with its own exit criteria if adopted)

- **S1 OCR for scanned PDFs:** Tesseract through `pytesseract` behind a feature flag. Exit criteria: F1 ≥ 0.75 on a scanned test subset, and p95 < 15 s.
- **S2 Candidate deletion and retention policy:** `DELETE /candidates/{id}`, plus TTL purge jobs.
- **S3 Taxonomy admin UI:** a small web UI for the emerging-skill review queue.
- **S4 Learning-to-rank:** train a LightGBM ranker on the matching features using the gold labels; it must beat the tuned linear scorer on val NDCG.
- **S5 Domain-specific embeddings:** fine-tune sentence-transformers on (alias, canonical) pairs; it must improve normalization recall by ≥ 2 points.
- **S6 Multi-language resumes:** start with Spanish, German and French.

### Exit criteria (release)

| # | Check | Pass condition |
|---|---|---|
| 11-A | A clean-machine install | `git clone`, `docker compose up -d`, then `scripts/demo.sh` succeeds on a fresh machine with only Docker installed |
| 11-B | Tag and changelog | `v1.0.0` tag exists; the CHANGELOG covers all phases |
| 11-C | Docs current | `CLAUDE.md`, `README.md` and `ordered.md` (status tracker all ✅) are up to date |

---

## Progress record template

Copy this to `docs/progress/phase-NN.md` when a phase is complete:

```markdown
# Phase NN — <name> — Progress Record

- **Completed by:** <agent/person>   **Date:** YYYY-MM-DD   **Git SHA:** <sha, or "uncommitted">
- **LLM quota used:** <approx. requests; model(s)>
- **Status:** ✅ Complete | ⛔ Blocked

## Exit criteria results
| # | Check | Command run | Result / metric | Pass? |
|---|---|---|---|---|
| N-A | ... | `...` | ... | ✅/❌ |

## Iteration log (metrics phases only)
| Iteration | Change | Metric before → after |
|---|---|---|

## Deviations from plan
- <what changed, why, link to ADR>

## Known issues / follow-ups
- ...

## Handoff notes for the next phase
- <anything the next agent must know: env vars added, data regenerated, gotchas>
```
