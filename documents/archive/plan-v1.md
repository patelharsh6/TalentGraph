# TalentGraph: Project Plan

> **Purpose of this document.** This is the master design for TalentGraph. It explains *what* we are building, *why* each design choice was made, and *how* the pieces fit together. The step-by-step execution order lives in [`ordered.md`](ordered.md). The original problem statement lives in [`idea.md`](idea.md).
>
> If this plan and `idea.md` conflict, `idea.md` wins on requirements and this plan wins on implementation choices. Record any deviation in the [Decision Log](#14-decision-log).

---

## Table of contents

1. [Vision and scope](#1-vision-and-scope)
2. [Success metrics](#2-success-metrics)
3. [Technology decisions](#3-technology-decisions)
4. [System architecture](#4-system-architecture)
5. [Agent message protocol](#5-agent-message-protocol)
6. [Agent designs](#6-agent-designs)
7. [Data model](#7-data-model)
8. [API design](#8-api-design)
9. [Observability](#9-observability)
10. [Datasets and evaluation](#10-datasets-and-evaluation)
11. [Repository layout](#11-repository-layout)
12. [Engineering conventions](#12-engineering-conventions)
13. [Risks and mitigations](#13-risks-and-mitigations)
14. [Decision log](#14-decision-log)
15. [Glossary](#15-glossary)

---

## 1. Vision and scope

### 1.1 Problem

Applicant tracking systems match resumes by literal keywords, so they miss obvious equivalents: `React.js`, `ReactJS` and `React` look different to them, and so do `ML Engineering` and `Machine Learning Engineering`. Resumes also arrive in many formats and layouts. As a result, qualified candidates are filtered out and irrelevant ones are surfaced.

### 1.2 Solution in one paragraph

TalentGraph is a multi-agent pipeline:

1. A **Parsing Agent** turns any resume (PDF, DOCX or TXT) into structured JSON.
2. A **Normalization Agent** maps every skill to a canonical node in a hierarchical taxonomy. It also infers implied skills, estimates proficiency, and flags unknown skills.
3. A **Matching Agent** scores a candidate against a job description using embeddings, weighted requirements and experience depth, and explains any gaps.
4. An **Orchestrator** runs these agents with retries, concurrency, partial-result degradation and full tracing.

Everything is exposed through a documented, authenticated, rate-limited REST API, with Python and JavaScript SDKs.

### 1.3 In scope

| Area | Included |
|---|---|
| Input formats | PDF (text-based), DOCX, TXT, and LinkedIn "Save to PDF" exports, which are treated as PDFs |
| Layouts | Single-column, multi-column, tabular and "creative" layouts (sidebars, icons, text boxes) |
| Extracted entities | Personal info, experience, education, skills, certifications, projects, publications |
| Taxonomy | At least 5,000 skills in a 4-level hierarchy, with aliases, implication rules and an emerging-skill review queue |
| Matching | Semantic plus weighted scoring, experience depth, gap analysis, upskilling paths, configurable threshold |
| Orchestration | LangGraph state machine, batch concurrency, retries, graceful degradation, per-agent traces |
| API | Every endpoint in `idea.md`, plus job status, health and metrics; API keys; rate limiting; webhooks |
| Delivery | Docker Compose stack, OpenAPI docs, Python and JS SDKs, evaluation harness and reports |

### 1.4 Out of scope (for v1)

The following are left out of v1. Each one can be revisited and recorded in the Decision Log.

- OCR for scanned or image-only PDFs. The parser detects these and returns `422 unsupported_content` with a hint. OCR (Tesseract) is listed as a stretch goal in Phase 11.
- A front-end UI. The only interfaces are Swagger UI and ReDoc.
- Multi-tenant data isolation beyond per-API-key ownership of candidates and jobs.
- Languages other than English.
- Kubernetes or cloud deployment. Docker Compose is the deployment target.

---

## 2. Success metrics

`idea.md` gives the evaluation criteria. This plan turns them into numeric **targets**, and every phase's exit criteria in `ordered.md` refer back to them. The targets are our own choices and can be tuned, but change them only through the Decision Log.

| # | Metric | How it is measured | Target |
|---|---|---|---|
| M1 | Parsing accuracy | Field-level micro F1 against ground-truth JSON on the held-out test split | **≥ 0.85** overall; **≥ 0.95** for name, email and phone |
| M2 | Normalization precision | Correct canonical ID ÷ predicted mappings on the labeled alias set | **≥ 0.90** precision, **≥ 0.85** recall |
| M3 | Matching quality | NDCG@10 per job, and Spearman ρ against expert scores | **NDCG@10 ≥ 0.80**, **ρ ≥ 0.60** |
| M4 | API completeness | Endpoint coverage vs. spec, OpenAPI lint, error-contract tests | **100%** of the endpoints in §8; 0 lint errors |
| M5 | Orchestration reliability | Success rate under concurrent load (Locust) | **≥ 99%** of requests succeed (or return partial results) at 50 concurrent users |
| M6 | End-to-end latency | Wall-clock time for `POST /parse` on one resume | **p95 < 10 s** and p50 < 5 s |

A "success" for M5 is a 2xx response, including a partial result with `status: "partial"`. A 5xx response or a timeout counts as a failure.

On the Gemini free tier, M5 is measured with `LLM_MODE=stub` (a simulated LLM with realistic latency), because the free quota cannot sustain 50 concurrent users. M6 is measured with the real Gemini API, one request at a time within the per-minute quota (see D10).

---

## 3. Technology decisions

| Concern | Choice | Why |
|---|---|---|
| Language | **Python 3.12** | Required by the brief, and it has the best ecosystem for NLP and ML. |
| Package manager | **uv** | Fast, gives a lockfile, and behaves the same on Windows, Linux and Docker. |
| Orchestration | **LangGraph** | Explicit state graph, conditional edges for degradation, built-in checkpointing, and deterministic control flow. A plain chat-agent framework would not give us this. |
| LLM | **Google Gemini API, free tier**, through the official `google-genai` SDK. Default `gemini-3.8-flash`, with `gemini-3.5-flash-lite` as the fallback when the quota runs out | Costs nothing, supports structured JSON output that follows a Pydantic schema, and is fast enough for the latency budget. See §3.1. |
| Embeddings | **sentence-transformers**, default `all-MiniLM-L6-v2` (384-d); can be configured to use `all-mpnet-base-v2` | Runs locally and fast on CPU, with no per-call cost. |
| Vector DB | **ChromaDB** (server mode in Docker) | Simple, open source, and has metadata filters. Wrapped behind a `VectorStore` interface so it can be swapped later. |
| Relational DB | **PostgreSQL 16** with SQLAlchemy 2.0 (async) and Alembic | Required by the brief. Holds the taxonomy tree, candidates, jobs, API keys and traces. |
| Queue / cache | **Redis 7** as the broker, with **Celery 5** for workers (Flower is an optional UI for watching them) | Celery is the most widely used Python task queue, with built-in retries, `acks_late` crash recovery and routing. Redis also handles rate limiting, the LLM quota counters and the parse-result cache. |
| API | **FastAPI** with Pydantic v2 | Generates OpenAPI automatically and handles request validation. |
| PDF | **PyMuPDF** for text blocks with bounding boxes and fonts; **pdfplumber** for table extraction | Layout analysis needs coordinates and font metadata, and pdfplumber is better at tables. |
| DOCX | **python-docx** | Required by the brief. Reads paragraphs, tables, styles and text boxes (the last through XML). |
| Fuzzy matching | **rapidfuzz** | Fast string similarity for alias lookup. |
| Dates | **dateparser** plus custom range parsing | Handles "Jan 2020 – Present", "2019–21" and similar. |
| Retries | **tenacity** | Declarative retry and backoff. |
| Logs / traces / metrics | **structlog**, **OpenTelemetry** (exported to Jaeger), **prometheus-client** | See §9. |
| Testing | **pytest**, pytest-asyncio, httpx `AsyncClient`, **Locust** for load | |
| Quality | **ruff** (lint and format), **mypy** (strict on `src/`), pre-commit | |
| Deployment | **Docker** and **Docker Compose** | Required by the brief. |

### 3.1 LLM usage policy

The LLM is used **only where rules cannot work**. That keeps us within the latency budget and the free-tier quotas, and lets the system degrade gracefully when the LLM is unavailable.

| Use | Where | Call pattern |
|---|---|---|
| Structured resume extraction (experience, education, projects and so on) | Parsing Agent | **One call per resume**: `client.aio.models.generate_content()` with `response_mime_type="application/json"` and `response_schema=<Pydantic model>`. The response text is validated again with `Model.model_validate_json()`. |
| Disambiguating ambiguous skills | Normalization Agent | **One batched call per resume**, covering only the skills that rules and embeddings could not resolve. The model chooses from the top-k candidate IDs or answers `NEW`. |
| Parsing job descriptions | Matching Agent | One structured-output call per job description, cached by content hash. |
| Generating synthetic data and labels | `scripts/` (offline) | A **rate-limited, resumable generation script**. It writes a checkpoint after each item, so the work can span several days of free-tier quota. Gemini's Batch API isn't available on the free tier. |

**Free-tier constraints and how the design handles them:**

- **Quotas.** Free-tier limits (requests per minute, tokens per minute, requests per day) differ by model and change over time; check them in AI Studio (aistudio.google.com/rate-limit). `llm/client.py` enforces `LLM_RPM_LIMIT` and `LLM_RPD_LIMIT` with a token bucket in Redis that every process shares. When a 429 arrives or the daily quota is used up, it switches to `LLM_FALLBACK_MODEL`. If that fails too, the pipeline degrades to rules (`partial` status).
- **Data use.** On the free tier, Google can use prompts and responses to improve its products. **Only send synthetic or consented resumes to the free tier.** For production use with real PII, switch to a paid tier; it's a config change only. This is noted in the README and in the API docs.
- **Model churn.** Model IDs are config values (`LLM_MODEL`, `LLM_FALLBACK_MODEL`), never hard-coded. Check them against the current free-tier list (ai.google.dev/gemini-api/docs/pricing) at the start of each phase.

**Rules for every LLM call:**

- Every call goes through `talentgraph/llm/client.py` (`GeminiLLM`), which applies:
  - the model and fallback model from config
  - `temperature=0` for extraction
  - a timeout (`LLM_TIMEOUT_S`) and tenacity retries with exponential backoff on 429, 5xx and connection errors
  - the shared rate limiter and a process-wide concurrency semaphore (`LLM_MAX_CONCURRENCY`)
  - token and latency metrics, from `usage_metadata`
- Prompts are static files in `llm/prompts/`. The changing input goes at the end, so Gemini's implicit context caching can help when it applies.
- **Known SDK limitation:** `response_schema` can drop `Field(description=...)` on nested models. Put the important field guidance in the prompt text as well, and always validate the response with Pydantic.
- `LLM_MODE` sets which client is used:
  - `real`: `GeminiLLM`
  - `fake`: `FakeLLM`, which returns recorded fixtures
  - `stub`: `FakeLLM` with simulated latency (`LLM_STUB_LATENCY_MS`), used for load tests so they don't burn free quota
- **All unit tests use `FakeLLM`.** Only tests marked `@pytest.mark.llm` call the real API.
- If the LLM is down, over quota, or has no key configured, the parser falls back to its rule-based extractor. It marks the affected fields `confidence < 0.5` and `source: "rules"`. This is the graceful-degradation path.

---

## 4. System architecture

### 4.1 Container view

```
                 ┌──────────────────────────── docker compose ─────────────────────────────┐
 HR platform     │                                                                          │
 / job board ───▶│  api (FastAPI, uvicorn)  ──enqueue──▶  redis  ◀──consume── worker (Celery)│
   (SDK)         │      │   ▲  auth, rate limit,           │  cache,          │  runs the     │
                 │      │   │  validation                  │  rate limit      │  same graph   │
                 │      ▼   │                              │                  ▼              │
                 │  ┌─────────────────── Orchestrator (LangGraph) ───────────────────────┐  │
                 │  │  Parsing Agent ─▶ Normalization Agent ─▶ Matching Agent (optional)  │  │
                 │  └──────────┬──────────────────┬───────────────────┬──────────────────┘  │
                 │             ▼                  ▼                   ▼                     │
                 │        postgres            chromadb          Gemini API (external)        │
                 │  (taxonomy, candidates, (skill & job      sentence-transformers           │
                 │   jobs, keys, traces)    embeddings)       (in-process)                   │
                 │                                                                          │
                 │  jaeger (traces)   prometheus (metrics)   [optional: grafana]             │
                 └──────────────────────────────────────────────────────────────────────────┘
```

- **Synchronous path.** `POST /parse` and `POST /match` run the graph in-process inside the API container, which keeps latency low.
- **Asynchronous path.** `POST /parse/batch` stores the uploaded files, creates a `batch_job`, and enqueues one Celery task per file. Workers run the same graph. When every item is finished, the worker fires the webhook.

### 4.2 Pipeline (LangGraph state machine)

```
 START
   │
   ▼
 ingest ──(bad file)──▶ fail_fast ──▶ END            (422: no pipeline run)
   │
   ▼
 parse ──(error after retries)──▶ record_error ─┐
   │                                            │  parse failure = no usable data → status "failed"
   ▼                                            ▼
 normalize ──(error)──▶ record_error ──▶ persist (raw skills kept, status "partial")
   │
   ▼
 match? ──(no job given)──▶ persist
   │ (job given)
   ▼
 match ──(error)──▶ record_error ──▶ persist (profile kept, status "partial")
   │
   ▼
 persist ──▶ notify (webhook if async) ──▶ END
```

**Graph state** (`PipelineState`, Pydantic):

```
trace_id, job_id?, candidate_id?, input_meta{filename, mime, sha256, bytes},
raw_document?, parsed_resume?, skill_profile?, match_result?,
agent_runs: list[AgentRun], errors: list[AgentError], status: ok|partial|failed
```

**Rules for graceful degradation:**

| Failing agent | What is still returned | Status |
|---|---|---|
| Parsing: LLM step fails | Rule-based extraction (contact info, sections, raw skills by lexicon) | `partial` |
| Parsing: everything fails | Nothing usable | `failed` (HTTP 422 or 500 with an error body) |
| Normalization | Parsed resume plus raw, un-normalized skill strings | `partial` |
| Matching | Parsed resume plus skill profile, with `match_result: null` and an error | `partial` |

Each node is wrapped in a `run_agent()` helper. The helper:

- applies a per-agent timeout and tenacity retries (3 attempts with exponential backoff and jitter), retrying only on errors marked `retryable`
- records an `AgentRun` (start, end, latency, attempts, quality score, error) for each attempt
- opens an OpenTelemetry span

### 4.3 Concurrency model

- The API is async, and CPU-heavy work (PDF layout analysis, embedding) runs in a bounded `ThreadPoolExecutor` so it doesn't block the event loop.
- The embedding model loads **once per process** as a singleton and is warmed up at startup.
- Each Celery worker container runs with `--concurrency=4` (the prefork pool, on Linux in Docker), and the worker service scales horizontally (`docker compose up --scale worker=N`).
- Celery tasks are synchronous. Each task runs the async pipeline with `asyncio.run()` inside a worker process, and the DB engine and embedding model are set up once per process through the `worker_process_init` signal.
- Tasks use `acks_late=True` and `task_reject_on_worker_lost=True`, so an item whose worker crashes is redelivered.
- **Local Windows development:** Celery's prefork pool doesn't support Windows, so run the worker natively with `--pool=solo` (or `--pool=threads`). Docker Compose uses Linux containers, so prefork works there.
- LLM calls are limited by a per-process semaphore (`LLM_MAX_CONCURRENCY`, default 4) and the Redis rate limiter shared across processes (§3.1), which keeps all workers together under the free-tier quota.

### 4.4 Caching

| Cache | Key | TTL | Purpose |
|---|---|---|---|
| Parse result | `parse:{sha256(file)}:{pipeline_version}` | 7 days | Re-uploading the same file returns instantly. |
| JD parse | `jd:{sha256(text)}:{pipeline_version}` | 7 days | Avoids re-running JD extraction. |
| Alias lookup | In-process LRU, rebuilt from Postgres when the taxonomy version changes | n/a | Fast normalization. |
| Embeddings | Stored in Chroma, keyed by `skill_id` | permanent | Skill vectors are computed once per taxonomy version. |

`pipeline_version` is a constant in `talentgraph/__init__.py`. Bump it whenever parser or normalizer output changes, so stale cache entries are never served.

---

## 5. Agent message protocol

All agents communicate through a single envelope. Inside LangGraph, the envelope is carried in `PipelineState`. Across process boundaries (Celery tasks), it is serialized as JSON. This one envelope is the "shared message protocol" the brief asks for.

```python
class AgentMessage(BaseModel):
    message_id: UUID
    trace_id: UUID  # same for the whole pipeline run
    parent_id: UUID | None  # message that caused this one
    sender: AgentName  # "orchestrator" | "parser" | "normalizer" | "matcher"
    recipient: AgentName
    type: Literal["task", "result", "error", "heartbeat"]
    payload: dict  # validated against a per-type schema (below)
    created_at: datetime
    attempt: int = 1


class AgentResult(BaseModel):
    status: Literal["ok", "partial", "failed"]
    data: dict | None
    quality: QualityScore  # agent-specific confidence, 0..1, with breakdown
    latency_ms: int
    warnings: list[str] = []


class AgentError(BaseModel):
    agent: AgentName
    code: str  # e.g. "llm_timeout", "unsupported_layout"
    message: str
    retryable: bool
    attempt: int
```

Payload schemas are versioned (`schema_version: "1.0"`) and live in `talentgraph/core/schemas/`. They are the same Pydantic models the API returns, so every contract has exactly one definition.

**Quality scores** (used for observability and for the `meta.quality` field in API responses):

- **Parser:** the weighted mean of field confidences, with a penalty for missing core sections.
- **Normalizer:** the fraction of skills mapped with confidence ≥ 0.8, and the fraction sent to the emerging queue.
- **Matcher:** the coverage of job requirements that could be evaluated, and the margin between the score and the threshold.

---

## 6. Agent designs

### 6.1 Parsing Agent

**Input:** file bytes and a MIME type. **Output:** `ParsedResume`.

```
bytes ─▶ detect type (magic bytes, not extension) ─▶ extractor ─▶ LayoutDocument
      ─▶ section detector ─▶ rule extractors ─▶ LLM structured extraction ─▶ merge & validate ─▶ ParsedResume
```

1. **Type detection.**
   - The file type is read from its leading bytes: `%PDF` means PDF; a ZIP containing `word/document.xml` means DOCX; anything else is treated as text if it decodes as UTF-8 or Latin-1.
   - Files that fail detection are rejected.
   - Limits: 10 MB maximum, and 20 pages maximum for PDFs.
2. **Extraction to a common `LayoutDocument`.** A `LayoutDocument` is a list of `Block{text, page, bbox, font_size, bold, kind: paragraph|table|list}`.
   - **PDF:** PyMuPDF `page.get_text("dict")` gives spans with bounding boxes and fonts.
     - **Column detection:** cluster the block x-centers with 1-D k-means (k = 1..3, picked by silhouette score), and treat a full-width block as a separator.
     - **Reading order:** go column by column, top to bottom.
     - **Tables:** pdfplumber `find_tables()` locates tables; their regions are converted to `table` blocks.
     - **Scanned PDFs:** if the text-to-page-area ratio is below a threshold, return `unsupported_content`.
   - **DOCX:** body paragraphs and tables in document order. Text boxes (`w:txbxContent`) and header/footer content are pulled in through XML. Heading styles are kept as a signal.
   - **TXT:** each paragraph becomes a block, and uppercase lines or lines ending in a colon are flagged as candidate headers.
3. **Section detection.** The aim is to label each block as one of `contact | summary | experience | education | skills | certifications | projects | publications | other`. It combines:
   - a header lexicon of about 150 variants (for example "Professional Experience", "Work History", "Employment")
   - typography cues (larger or bold text, short lines, all caps)
   - position (the contact section is usually at the top or in the sidebar)
   - a fallback for blocks with no header: a lightweight classifier (TF-IDF plus logistic regression, trained on the synthetic set)
4. **Rule extractors.** These are deterministic and run first:
   - email, phone (`phonenumbers` library), URLs (LinkedIn, GitHub, portfolio)
   - date ranges, which are normalized to `YYYY-MM` with `is_current`
   - location, using a gazetteer of the top cities and countries
   - a candidate skill list: n-gram lookup against the taxonomy alias index
5. **LLM structured extraction.**
   - **Input:** the section-labeled text in reading order. The prompt includes the section labels and the rule-extracted hints.
   - **Output:** a Pydantic `ResumeExtraction`. Each field carries `confidence` and `evidence`, a short span of the source text.
   - The system prompt and schema are static and come first, so implicit caching can apply to them.
6. **Merge and validate.**
   - When rules and the LLM disagree on contact fields, the rules win, because regex is reliable for those.
   - The LLM wins on structured entities.
   - Validation checks: dates are in order, emails are valid, and duration is computed for each role.
   - Output: `ParsedResume`, with `meta.source` per field (`rules` | `llm` | `merged`).

**`ParsedResume` (abridged):**

```
personal: {name, email, phone, location{city, region, country}, links[]}
summary?
experience[]: {company, title, location?, start, end?, is_current, duration_months, responsibilities[], skills_mentioned[]}
education[]: {institution, degree, field, start?, end?, grade?}
skills[]: {raw, category_hint: technical|soft|unknown, evidence}
certifications[]: {name, issuer?, date?, expires?, credential_id?}
projects[]: {name, description, technologies[], url?, dates?}
publications[]: {title, venue?, date?, authors[]?, url?}
meta: {layout: single|multi|table|creative, pages, confidence, field_sources}
```

### 6.2 Skill Taxonomy and Normalization Agent

**Input:** the parsed resume. **Output:** `SkillProfile`, a list of canonical skills with proficiency, inferred skills, and emerging skills.

**Taxonomy shape.** There are 4 levels: **Domain → Category → Subcategory → Skill**. For example: `Technical Skills → Programming Languages → General-Purpose → Python`, or `Technical Skills → AI/ML → Deep Learning Frameworks → PyTorch`.

The taxonomy has three supporting structures:

- **Skills.** Each skill has a stable `slug`, a `type` (technical, soft or domain), a description, and alias rows.
- **Implication rules.** For example, `{TensorFlow, PyTorch, Keras} ≥ 1 → Deep Learning (confidence 0.8)` and `{Kubernetes} → Container Orchestration`. Every skill also implies its ancestors at reduced weight.
- **Related edges** between skills, used for upskilling paths. For example, `Docker → Kubernetes` and `Pandas → Polars`.

**The normalization cascade** runs per raw skill string, and the first step that is confident enough wins:

| Step | Method | Accept when |
|---|---|---|
| 0 | Clean: lowercase, strip versions ("Python 3.11" → "python"), unify punctuation ("react.js", "react-js" → "reactjs"), split lists ("AWS/GCP") | n/a |
| 1 | Exact alias lookup (dict built from `skill_aliases`) | match, confidence 1.0 |
| 2 | Fuzzy match (rapidfuzz `token_sort_ratio`) against aliases | score ≥ 92 and unique top hit |
| 3 | Embedding nearest neighbor in Chroma `skills` collection | cosine ≥ 0.82 and margin over 2nd ≥ 0.05 |
| 4 | LLM disambiguation (batched): top-5 candidates per unresolved skill, plus the resume context | model picks an ID with confidence ≥ 0.7 |
| 5 | Otherwise: record it as an **emerging skill** | n/a |

Emerging skills are stored with an occurrence count and example contexts. Once a skill appears in at least 3 distinct resumes, it is surfaced through `GET /skills/emerging` for human review.

**Hierarchy inference.**

- Apply the implication rules to the set of mapped skills.
- Add their ancestors with `inferred: true` and a confidence of `rule_conf × min(child_conf)`.
- Inferred skills never outrank explicit evidence.

**Proficiency estimation.** The output is a level from 1 to 5 (Beginner, Elementary, Intermediate, Advanced, Expert), along with `years` and an explanation. The score is a weighted sum of these features:

| Feature | Source | Effect |
|---|---|---|
| `years_used` | The sum of the durations of roles whose responsibilities or `skills_mentioned` include the skill, merging overlaps | 0–2 y → 2, 2–5 y → 3, 5–8 y → 4, 8+ y → 5 (base) |
| Recency | Months since the last role that used the skill | −1 if more than 5 years ago |
| Qualifier phrases | Regex and lexicon over the evidence text: "expert in", "led", "architected" raise the level; "familiar with", "exposure to", "basic" lower it | ±1 |
| Breadth | The number of projects or roles that mention the skill | +1 if 3 or more |
| Certifications | A related certification | +1 (max 5) |
| Skills-section only | The skill is listed but has no supporting evidence | Capped at 2 |

The weights live in `config/proficiency.yaml` and are tuned in Phase 4.

### 6.3 Semantic Skill-to-Job Matching Agent

**Input:** a `SkillProfile` and either a job description (text or structured) or a stored `job_id`. **Output:** a `MatchResult`.

1. **Job parsing.** An LLM call (cached) extracts `JobRequirements`:
   - required and nice-to-have skills, each with an optional `min_years` and an `importance` (1–5)
   - the seniority level
   - education requirements
   - the role family

   These skills are normalized with the **same Normalization Agent**, so both sides share canonical IDs.
2. **Per-requirement credit.** For each requirement `r`, take the best candidate skill `c` and compute its similarity:
   - exact canonical ID: 1.0
   - `c` is a descendant of `r` (for example, the candidate has PyTorch and the job requires Deep Learning): 0.9
   - `c` is an ancestor of `r`, or a sibling within the same subcategory: 0.6
   - otherwise, the cosine similarity of the canonical skill embeddings if it is ≥ the floor (0.55); else 0

   Then compute `depth(c, r) = min(1, candidate_years / r.min_years)`, or a proficiency-based value if `min_years` is unset.

   The credit is `credit_r = sim × (0.6 + 0.4 × depth)`.
3. **Weighted skill score.** `S_skill = Σ w_r·credit_r / Σ w_r`. Each weight is `w_r = importance_r × (1.0 if required else λ_nice)`, with a default `λ_nice = 0.35`.
4. **Experience score.** `S_exp` blends three things:
   - total relevant years vs. the years required for the role's seniority
   - the role-family match between the candidate's titles and the job, using embedding similarity of the titles
   - project complexity signals: team-lead roles, scale words, number of projects
5. **Profile semantic score.** `S_sem` is the cosine similarity between an embedding of the whole candidate summary and the job text. It acts as a tiebreaker for soft fit.
6. **Final score.** `score = α·S_skill + β·S_exp + γ·S_sem − penalty`. The default weights are α 0.6, β 0.25, γ 0.15. The penalty is `0.1 × number of missing required skills with importance ≥ 4`, clamped to [0, 1]. The weights are tuned in Phase 4 to maximize NDCG@10 on the training split.
7. **Threshold.** The result is `is_match = score ≥ threshold`. The request can pass `threshold`, or one of these presets:

   | Preset | Threshold |
   |---|---|
   | `precision` | 0.75 |
   | `balanced` | 0.60 |
   | `recall` | 0.45 |

   The presets are calibrated on the validation split; the precision/recall curve is in the evaluation report.
8. **Gap analysis.** For each unmet or partly met requirement, the result returns the missing skill, the current level and the required level. It also returns an **upskilling path**:
   - **Adjacent skills:** skills the candidate already has that are linked to the missing skill by `related` or sibling edges ("you know Docker, so learn Kubernetes next").
   - **Prerequisite order:** the order comes from the implication and ancestor edges, with an estimated effort (S, M or L) based on the hierarchy distance.
9. **Explainability.** Every `MatchResult` includes a per-requirement breakdown: which candidate skill matched, the similarity type, the depth, and the credit. Recruiters can see why a candidate scored as they did.

### 6.4 Orchestrator

The orchestrator is covered in §4.2–4.4. Its responsibilities:

- **Lifecycle:** agents are classes with `startup()` and `shutdown()` hooks (load models, warm caches) registered in an `AgentRegistry`. The FastAPI lifespan and the Celery `worker_process_init` and `worker_process_shutdown` signals call these hooks.
- **Delegation:** LangGraph nodes call agents through the registry, passing `AgentMessage` envelopes.
- **Batch mode:** a Celery fan-out with one task per file. A `batch_job` row tracks per-item progress, and the job completes when all items reach a terminal state.
- **Retry and degradation:** `run_agent()` handles both (§4.2).
- **Observability:** spans, metrics and `agent_runs` rows (§9).

---

## 7. Data model

### 7.1 PostgreSQL (abridged)

```
skills(id PK, slug UNIQUE, name, type, level SMALLINT, parent_id FK→skills, description, taxonomy_version, created_at)
skill_aliases(id PK, skill_id FK, alias, alias_normalized UNIQUE, source)
skill_implications(id PK, antecedent_ids INT[], consequent_id FK, min_count, confidence)
skill_relations(skill_id FK, related_id FK, kind: related|prerequisite, weight)
emerging_skills(id PK, normalized_text UNIQUE, occurrences, example_contexts JSONB, status: pending|approved|rejected|merged, merged_into FK?, reviewed_by, reviewed_at)

api_keys(id PK, key_prefix, key_hash, name, owner, scopes TEXT[], rate_limit_per_min, webhook_secret, active, created_at, last_used_at)
candidates(id UUID PK, api_key_id FK, file_sha256, parsed JSONB, quality REAL, pipeline_version, created_at)
candidate_skills(candidate_id FK, skill_id FK, proficiency SMALLINT, years REAL, inferred BOOL, confidence REAL, evidence JSONB, PK(candidate_id, skill_id))
jobs(id UUID PK, api_key_id FK, title, raw_text, requirements JSONB, text_sha256, created_at)
matches(id UUID PK, candidate_id FK, job_id FK, score REAL, threshold REAL, is_match BOOL, breakdown JSONB, gaps JSONB, created_at)

batch_jobs(id UUID PK, api_key_id FK, status: queued|running|completed|completed_with_errors|failed, total, succeeded, failed, partial, callback_url, created_at, finished_at)
batch_items(id UUID PK, batch_job_id FK, filename, status, candidate_id FK?, error JSONB)
webhook_deliveries(id PK, batch_job_id FK, url, attempt, status_code, response_ms, next_retry_at, delivered_at)

agent_runs(id PK, trace_id UUID, agent, attempt, status, latency_ms, quality REAL, error_code, started_at)
```

### 7.2 ChromaDB collections

| Collection | ID | Document | Metadata |
|---|---|---|---|
| `skills` | `skill_id` | Canonical name, top aliases and description | `type`, `level`, `parent_id`, `taxonomy_version` |
| `job_titles` | Normalized title | Title | `role_family` |

Candidate-level embeddings (summaries) are computed on the fly and are not stored in v1.

---

## 8. API design

**Base path:** `/api/v1`. **Auth:** the `X-API-Key` header. **Content type:** JSON, or `multipart/form-data` for uploads. **Docs:** Swagger UI at `/docs`, ReDoc at `/redoc`, and the schema at `/openapi.json`.

| Method | Path | Description | Sync / async |
|---|---|---|---|
| POST | `/parse` | Upload one resume. Returns `candidate_id`, the parsed resume, the skill profile and `meta`. Optional `?include=trace`. | Sync |
| POST | `/parse/batch` | Upload up to 100 files, or a ZIP of them, with an optional `callback_url`. Returns `202` with `batch_job_id`. | Async |
| GET | `/jobs/{batch_job_id}` | Batch status and per-item progress. | n/a |
| GET | `/jobs/{batch_job_id}/results` | Paginated per-item results. | n/a |
| GET | `/candidates/{id}` | Full parsed candidate. | n/a |
| GET | `/candidates/{id}/skills` | Skill profile, filterable by `type`, `min_proficiency` and `include_inferred`. | n/a |
| POST | `/match` | `{candidate_id, job: {title, description} \| job_id, threshold? \| preset?}` returns a `MatchResult`. | Sync |
| POST | `/match/rank` | Rank up to N candidates for one job. A stretch goal that supports the NDCG evaluation. | Sync |
| GET | `/skills/taxonomy` | Browse the tree: `?parent_id=`, `?depth=`, paginated. | n/a |
| GET | `/skills/search` | `?q=` uses alias, fuzzy and semantic search. | n/a |
| GET | `/skills/{id}` | Skill detail: ancestors, children, aliases, related skills. | n/a |
| GET | `/skills/emerging` | Review queue (admin scope). | n/a |
| POST | `/skills/emerging/{id}/review` | `approve` (create a skill), `merge` (into an existing skill as an alias) or `reject` (admin scope). | n/a |
| GET | `/health` | Liveness check. Not authenticated. | n/a |
| GET | `/ready` | Readiness check: DB, Redis, Chroma and the model are loaded. Not authenticated. | n/a |
| GET | `/metrics` | Prometheus metrics. Internal, so not routed through the public prefix. | n/a |

The API reference uses `/skills/taxonomy` as the canonical name for the taxonomy endpoint in `idea.md`, and `/skills/search` sits under it.

### 8.1 Cross-cutting behaviour

- **Authentication.**
  - Keys look like `tg_live_<32 random chars>`. Only a SHA-256 hash and an 8-character prefix are stored.
  - Each key has scopes: `parse`, `match`, `read` and `admin`.
  - A missing or invalid key returns `401`, and a missing scope returns `403`.
- **Rate limiting.**
  - A Redis sliding window is applied per key, at `rate_limit_per_min` (default 60), plus a separate, lower limit for batch submissions.
  - Every response carries `X-RateLimit-Limit`, `X-RateLimit-Remaining` and `X-RateLimit-Reset`.
  - A request over the limit gets `429` with `Retry-After`.
- **Validation.** Pydantic models validate request bodies. Uploads are checked for MIME type and magic bytes, a 10 MB maximum, and 100 files maximum per batch.
- **Errors.** All errors use **RFC 7807 `application/problem+json`**:

  ```json
  {"type": "https://talentgraph.dev/errors/unsupported_file_type", "title": "Unsupported file type",
   "status": 415, "detail": "Detected image/png; expected PDF, DOCX or TXT.",
   "instance": "/api/v1/parse", "trace_id": "…", "errors": [ /* field-level validation errors */ ]}
  ```

  An error catalog (`docs/errors.md`) lists every `type`.
- **Idempotency.** An optional `Idempotency-Key` header on POST endpoints stores the response in Redis for 24 hours.
- **Webhooks.**
  - When a batch finishes, the service sends `POST callback_url` with `{event: "batch.completed", batch_job_id, status, counts, results_url}`.
  - It is signed with `X-TalentGraph-Signature: t=<ts>,v1=<hex HMAC-SHA256(secret, ts + "." + body)>`, where the secret is per API key.
  - Delivery is retried 5 times with exponential backoff (10 s up to 1 h), and each attempt is logged in `webhook_deliveries`.
- **Pagination.** Cursor-based: `?limit=&cursor=`. Responses include `next_cursor`.
- **Response envelope for pipeline endpoints.** These return `{data, meta: {status, trace_id, pipeline_version, latency_ms, quality, warnings[], trace?}}`.

### 8.2 SDKs

- **Python (`sdks/python`).** A `talentgraph` package with a sync and an async client built on httpx. It includes typed models generated from OpenAPI with `datamodel-code-generator`, retries on 429 and 5xx that respect `Retry-After`, and a `wait_for_batch()` helper.
- **JavaScript/TypeScript (`sdks/js`).** A `@talentgraph/sdk` package using `fetch`. Its types are generated from OpenAPI with `openapi-typescript`, and it has the same helpers. It works in Node 18+.
- **Examples.** `examples/` holds a cURL walkthrough, Python and JS scripts for each endpoint, and a webhook receiver example (FastAPI and Express) that verifies signatures.

---

## 9. Observability

| Signal | Implementation | Key items |
|---|---|---|
| Logs | structlog JSON to stdout | `trace_id`, `agent`, `attempt`, `latency_ms` on every line; no resume PII at INFO level |
| Traces | OpenTelemetry SDK exported over OTLP to Jaeger, with FastAPI and Celery instrumentation | One trace per pipeline run (it continues across the API → Celery boundary), one span per agent and attempt, child spans for LLM calls, embedding, and DB access |
| Metrics | prometheus-client at `/metrics` | `tg_agent_latency_seconds{agent}` (histogram), `tg_agent_runs_total{agent,status}`, `tg_agent_quality{agent}` (histogram), `tg_llm_tokens_total{kind}`, `tg_llm_latency_seconds`, `tg_pipeline_total{status}`, `tg_http_requests_total{route,code}`, `tg_batch_queue_depth`, `tg_emerging_skills_pending` |
| Per-request trace | `agent_runs` table, plus `?include=trace` on `/parse` and `/match` | Returns the agent timeline with latency, attempts and quality, for debugging by API consumers |
| Dashboards (optional) | Grafana provisioned from `deploy/grafana/` | Latency p50/p95 by agent, error rate, queue depth, LLM spend |

**PII.** Resumes contain personal data.

- Log only IDs and hashes.
- `agent_runs` stores no payloads.
- Uploaded files are deleted after processing unless `RETAIN_UPLOADS=true`.
- A `DELETE /candidates/{id}` endpoint may be added in Phase 11 for data-subject requests.

---

## 10. Datasets and evaluation

### 10.1 Datasets (built in Phase 1)

| Dataset | Size | How it is built | Location |
|---|---|---|---|
| Skill taxonomy | ≥ 5,000 skills, ≥ 15,000 aliases | Seeded from **ESCO** (EU skills/occupations, CC-BY 4.0) and **O\*NET** technology skills (CC-BY 4.0), restructured into our 4-level tree. Tech skills are enriched with a curated list (languages, frameworks, cloud, data, ML, DevOps). Aliases come from source alt-labels, curated abbreviations (JS, K8s, TF, GCP…) and LLM-proposed aliases that a human spot-checks. | `data/taxonomy/*.csv` plus a loader |
| Synthetic resumes | ≥ 500 (≥ 10 industries) as PDF and DOCX, with some TXT | Generate a **ground-truth JSON profile first** (Faker for names and contact details; Gemini for realistic content, through the rate-limited and resumable generator). Then **render** it with ≥ 6 templates: single-column, two-column, sidebar, table-based, creative (icons and text boxes), minimal TXT. PDFs are built with ReportLab; DOCX with python-docx. Because the profile comes first, labels are exact. | `data/resumes/{train,val,test}/` with `*.pdf\|docx\|txt` and `*.gt.json` |
| Job descriptions | ≥ 100 (engineering, data science, PM, design and more) | LLM-generated from role templates, with ground-truth requirements JSON | `data/jobs/` |
| Normalization gold set | ≥ 1,000 (raw string → skill_id) pairs | Drawn from synthetic resumes plus hand-written hard cases (typos, versions, abbreviations, ambiguous terms such as "Go" and "R") | `data/eval/normalization_gold.csv` |
| Matching gold set | 100 jobs × 20 candidates = 2,000 pairs with a 0–4 relevance score | Graded by an **LLM judge with a written rubric** (its model differs from the matcher's prompts). **At least 200 pairs are double-labeled by humans**, and we report agreement (Cohen's κ). Note: this is a proxy for "expert-labeled". | `data/eval/match_gold.csv` |

**Splits:** 70/15/15 for train/val/test, stratified by industry and template. **The test split is never used for tuning.**

### 10.2 Evaluation harness (`eval/`)

Each script writes a JSON and a Markdown report to `reports/` with a timestamp and the git SHA. The `reports/` directory is gitignored except for `reports/baseline/`.

| Script | Measures | Metric |
|---|---|---|
| `eval/parsing.py` | Field-level precision, recall and F1, broken down by field, template and format. Fields are matched with normalized string comparison, plus fuzzy matching (≥ 0.9) for free text. List entities (experience, education) are aligned with Hungarian matching. | M1 |
| `eval/normalization.py` | Precision, recall and the emerging-flag rate on the gold set; a confusion list of the worst errors | M2 |
| `eval/matching.py` | NDCG@5 and @10 per job, Spearman/Kendall vs. gold, and the precision/recall curve over thresholds | M3 |
| `eval/api_contract.py` | Hits every endpoint in §8 with valid and invalid inputs, and lints the OpenAPI spec (`openapi-spec-validator` and Spectral) | M4 |
| `eval/load/locustfile.py` | Concurrent parse, match and batch mix; success rate and latency | M5, M6 |
| `eval/latency.py` | 50 sequential single parses from the test split; p50, p95, p99 and a per-agent breakdown | M6 |

---

## 11. Repository layout

```
TalentGraph/
├── idea.md  plan.md  ordered.md  CLAUDE.md  README.md
├── pyproject.toml  uv.lock  .env.example  .pre-commit-config.yaml
├── docker-compose.yml  Dockerfile  deploy/ (prometheus.yml, grafana/)
├── alembic.ini  migrations/
├── config/                 # proficiency.yaml, matching.yaml, section_lexicon.yaml
├── src/talentgraph/
│   ├── __init__.py         # __version__, PIPELINE_VERSION
│   ├── config.py           # pydantic-settings; all env vars
│   ├── core/               # schemas/ (ParsedResume, SkillProfile, MatchResult, AgentMessage…), errors.py, ids.py
│   ├── llm/                # client.py (Gemini wrapper), fake.py (FakeLLM), ratelimit.py, prompts/
│   ├── embeddings/         # encoder.py (singleton), vector_store.py (Chroma impl + interface)
│   ├── db/                 # models.py, session.py, repositories/
│   ├── agents/
│   │   ├── base.py         # Agent protocol, AgentRegistry, run_agent()
│   │   ├── parsing/        # detect.py, pdf.py, docx.py, text.py, layout.py, sections.py, rules.py, llm_extract.py, agent.py
│   │   ├── normalization/  # clean.py, cascade.py, hierarchy.py, proficiency.py, emerging.py, agent.py
│   │   └── matching/       # job_parser.py, scoring.py, gaps.py, thresholds.py, agent.py
│   ├── orchestrator/       # state.py, graph.py, batch.py
│   ├── worker/             # celery_app.py (Celery config + signals), tasks.py (parse_item, finalize_batch, deliver_webhook)
│   ├── api/                # main.py, deps.py, auth.py, ratelimit.py, problems.py, idempotency.py, webhooks.py, routers/
│   └── observability/      # logging.py, tracing.py, metrics.py
├── scripts/                # build_taxonomy.py, gen_profiles.py, render_resumes.py, gen_jobs.py, label_matches.py, seed.py, create_api_key.py
├── data/                   # taxonomy/, resumes/, jobs/, eval/   (large binaries via Git LFS or regenerated by scripts)
├── eval/                   # parsing.py, normalization.py, matching.py, api_contract.py, latency.py, load/
├── tests/
│   ├── unit/               # pure logic, FakeLLM, no network
│   ├── integration/        # needs docker compose services (marker: integration)
│   ├── e2e/                # full API flows (marker: e2e)
│   └── fixtures/           # small resumes, JDs, LLM fixture responses
├── sdks/python/  sdks/js/
├── examples/
├── docs/                   # architecture.md, errors.md, runbook.md, decisions/ (ADRs), progress/
└── reports/
```

---

## 12. Engineering conventions

- **Config:** all settings come from environment variables through `talentgraph.config.Settings` (pydantic-settings). Never read `os.environ` directly elsewhere. `.env.example` lists every variable.
- **Schemas first:** every cross-component contract is a Pydantic model in `core/schemas`. API responses re-use the same models, never ad-hoc dicts.
- **Determinism:** rule steps and scoring are pure functions that are unit-tested without I/O. Randomness (data generation, k-means) is seeded.
- **Test markers:** `unit` is the default, then `integration`, `e2e`, `llm` (real API calls, never run in default CI) and `slow`. The default `pytest` run must pass offline in under 60 seconds.
- **Coverage:** at least 80% line coverage on `src/talentgraph/agents` and `src/talentgraph/api`.
- **Versioning:** `PIPELINE_VERSION` changes whenever output semantics change, and `taxonomy_version` changes whenever the taxonomy is reloaded. Both appear in API `meta`.
- **ADRs:** a decision that changes this plan gets a short ADR in `docs/decisions/NNNN-title.md` and a row in §14.
- **Progress records:** when a phase's exit criteria pass, write `docs/progress/phase-NN.md` with the commands you ran, their outputs and metric values (see `ordered.md`).

---

## 13. Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| LLM latency pushes `POST /parse` over 10 s | M6 fails | One extraction call per resume to a Flash model with `temperature=0` and a static prompt prefix. Rules and embeddings handle most normalization. Return a hash cache hit in milliseconds. If the p95 budget is at risk, emit a warning and degrade to rules after the `LLM_TIMEOUT_S` deadline. |
| LLM unavailable or rate-limited | Pipeline failures | Retries, the shared rate limiter, the fallback model, and degradation to rules (`partial` status). |
| **Free-tier quota exhausted** (data generation, load tests, demos) | Blocked work, M5 and M6 can't be measured | Resumable generation scripts with checkpoints. Load tests use `LLM_MODE=stub` with realistic simulated latency. Real-LLM latency (M6) is measured sequentially, within the per-minute quota. Record quota usage in each progress record. |
| **Free-tier data use** (Google can use prompts to improve its products) | Privacy and compliance | Only synthetic or consented resumes on the free tier. A paid key is required before real PII is processed (README warning). |
| Synthetic data is too clean, so metrics are inflated | Misleading evaluation | ≥ 6 diverse templates, noise injection (typos, odd date formats, missing sections, two-column reorder), and ≥ 20 real public-domain or consented sample resumes for qualitative checks. |
| The "expert" matching labels are synthetic | Weak M3 claim | Human double-labeling of ≥ 200 pairs, with κ reported. Be transparent in the report. |
| Ambiguous skills ("Go", "R", "Spring", "Swift") | Normalization errors | Context-aware LLM disambiguation step. Ambiguous aliases are flagged `ambiguous=true` and always routed to step 4 when context is available. |
| Taxonomy licensing | Legal | Use only CC-BY sources (ESCO, O\*NET), keep attribution in `data/taxonomy/ATTRIBUTION.md`, and avoid scraping proprietary taxonomies. |
| PII leakage | Compliance | Log hygiene, no payloads in traces, upload deletion, and API-key data ownership checks. |
| Windows development vs. Linux containers | "Works on my machine" | Integration tests run against Docker Compose. `uv` lockfile. Avoid OS-specific libraries (for example `python-magic`) by using pure-Python detection. |

---

## 14. Decision log

| # | Date | Decision | Reason |
|---|---|---|---|
| D1 | 2026-10-02 | LangGraph for orchestration | Explicit graph and conditional edges for degradation |
| D2 | 2026-10-02 | ARQ instead of Celery *(superseded by D8)* | Async-native, Redis-only, simpler |
| D3 | 2026-10-02 | ChromaDB as the vector store | Easiest to self-host; abstracted behind an interface |
| D4 | 2026-10-02 | Claude `claude-opus-5-5` with structured outputs *(superseded by D9)* | Accuracy on messy layouts, with a bounded latency and cost budget |
| D5 | 2026-10-02 | Taxonomy seeded from ESCO and O\*NET | Open license and large coverage |
| D6 | 2026-10-02 | Matching gold labels from an LLM judge plus a human-labeled subset | No real expert labels available |
| D7 | 2026-10-02 | Scanned-PDF OCR out of scope for v1 | Not required by the brief; keeps the latency budget |
| D8 | 2026-10-02 | **Celery** (Redis broker) for background workers | Owner's choice: mature, widely known, and has built-in retries and acks_late recovery |
| D9 | 2026-10-02 | **Gemini API free tier** through `google-genai` (`gemini-3.8-flash`, falling back to `gemini-3.5-flash-lite`); LLM only for extraction and disambiguation | Owner's choice: no cost. Quota and data-use limits are handled by §3.1 |
| D10 | 2026-10-02 | Load tests use `LLM_MODE=stub`; real-LLM latency is measured sequentially | Free-tier quotas can't sustain 50 concurrent users |
| D11 | 2026-10-03 | Taxonomy built from **O\*NET 31.0 + Wikidata alt-labels + a curated layer**; ESCO and LLM aliases not used *(supersedes D5 in part; ADR-0001)* | ESCO's bulk download needs a manual form, so it isn't reproducible; no LLM quota in Phase 1; the first build padded its counts with placeholder skills |
| D12 | 2026-10-03 | Phase 1 match gold graded by a **deterministic rubric labeler**, not the LLM judge, until the judge or human labels are available *(supersedes D6 in part; ADR-0002)* | No Gemini quota in Phase 1; M3 must be re-validated with the LLM judge or human κ before Phase 4 sign-off |

Add new rows here. Never edit old rows; add a row that supersedes them instead.

---

## 15. Glossary

- **Canonical skill:** a node in our taxonomy, with a stable `slug` and ID.
- **Alias:** any surface form that maps to a canonical skill (`k8s` → `kubernetes`).
- **Implication rule:** evidence of some skills implies another (TensorFlow + PyTorch ⇒ Deep Learning).
- **Emerging skill:** a skill string that we couldn't map confidently. It is queued for human review.
- **Partial result:** the pipeline completed, but at least one agent failed. The response contains everything the successful agents produced.
- **Pipeline version:** a constant that identifies the semantics of the parser and normalizer output. It is part of every cache key.
