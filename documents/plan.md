# TalentGraph: Project Plan (v2)

> **Purpose of this document.** This is the master design for TalentGraph. It explains *what* we are building, *why* each design choice was made, and *how* the pieces fit together. The build order lives in [`ordered.md`](ordered.md). The original problem statement lives in [`idea.md`](idea.md). The one-page summary of the v2 re-scope is [`project-plan-v2.md`](project-plan-v2.md).
>
> **v2 (2026-10-13)** re-scopes the project as an AI-engineering portfolio piece (ADR-0003). The v1 plan is kept unchanged in [`archive/plan-v1.md`](archive/plan-v1.md). If this plan and `idea.md` conflict, this plan wins: the brief is the starting point, and every deviation is recorded in the [Decision Log](#14-decision-log).

---

## Table of contents

1. [Vision and scope](#1-vision-and-scope)
2. [Success metrics](#2-success-metrics)
3. [Technology decisions](#3-technology-decisions)
4. [System architecture](#4-system-architecture)
5. [Agent protocol](#5-agent-protocol)
6. [Agent designs](#6-agent-designs)
7. [Data model](#7-data-model)
8. [API design](#8-api-design)
9. [Web app and live demo](#9-web-app-and-live-demo)
10. [Datasets and evaluation](#10-datasets-and-evaluation)
11. [Repository layout](#11-repository-layout)
12. [Engineering conventions](#12-engineering-conventions)
13. [Risks and mitigations](#13-risks-and-mitigations)
14. [Decision log](#14-decision-log)
15. [Glossary](#15-glossary)

---

## 1. Vision and scope

### 1.1 Problem

Applicant tracking systems match resumes by literal keywords, so they miss obvious equivalents: `React.js`, `ReactJS` and `React` look different to them, and so do `K8s` and `Kubernetes`. Resumes arrive in many formats and layouts, and recruiters get a score with no explanation. Qualified candidates are filtered out and irrelevant ones are surfaced.

### 1.2 Goal

A **portfolio project for AI/ML engineering roles**. A reviewer opens the live demo and, within a few minutes, sees a working multi-agent AI system with **measured** quality, **grounded** LLM output and **responsible-AI** safeguards.

### 1.3 Solution in one paragraph

TalentGraph is a multi-agent pipeline orchestrated by LangGraph:

1. A **Parsing Agent** turns a resume (PDF, DOCX or TXT) into structured JSON. Every LLM-extracted field cites its source text, and a verifier checks that citation (F2).
2. A **Normalization Agent** maps every skill to a canonical node in a 9,600-skill taxonomy, infers implied skills, estimates proficiency and lists unrecognized skills. Its embedding model is fine-tuned on the taxonomy's aliases (F5).
3. A **Matching Agent** scores a candidate against a job, explains each requirement, lists gaps with upskilling hints, and can run **blind** (F4).
4. A **Talent Search agent** answers plain-English recruiter queries with tool calls over the database and vector store (F1).
5. A **Career Coach agent** turns a match into a learning plan, interview questions and truthful resume suggestions, checked by a critic step (F3).

A FastAPI REST API exposes everything, and a **Next.js web app** sits on top of it, hosted as a live demo.

### 1.4 In scope

| Area | Included |
|---|---|
| Input formats | PDF (text-based), DOCX, TXT. LinkedIn "Save to PDF" exports are treated as PDFs |
| Layouts | Single-column, multi-column, tabular and "creative" (sidebars, text boxes) |
| Extracted entities | Personal info, summary, experience, education, skills, projects, certifications (name, issuer) |
| Taxonomy | 9,642 skills in a 4-level hierarchy, 15,122 aliases, implication rules, related-skill edges |
| Matching | Semantic + weighted scoring, years depth, gap analysis, upskilling hints, threshold presets, blind mode |
| AI features | F1 NL search, F2 grounding, F3 Career Coach, F4 fairness, F5 fine-tuned embeddings + CI eval gate |
| Orchestration | LangGraph, retries, graceful degradation (`partial`), per-agent timings |
| API | §8 endpoints, one API key, slowapi rate limits, RFC 7807 errors |
| Front end | Next.js app (§9), hosted demo with cached sample data |
| Evaluation | M1–M10 on held-out data, published on the evaluation page |

### 1.5 Out of scope

- OCR for scanned or image-only PDFs. The parser returns `422 unsupported_content`.
- Celery workers, webhooks, SDK packages, distributed tracing and Prometheus metrics (ADR-0003).
- Multi-tenant data isolation and API-key scopes.
- Languages other than English.
- Kubernetes or production-grade cloud deployment. The demo runs on one small host.

---

## 2. Success metrics

`idea.md` gives the evaluation criteria. This plan turns them into numeric targets. Change a target only through an ADR and a Decision Log row.

| # | Metric | How it is measured | Target |
|---|---|---|---|
| M1 | Parsing accuracy | Field-level micro F1 against ground-truth JSON on the held-out test split | **≥ 0.85** overall; **≥ 0.95** for name, email and phone |
| M2 | Normalization quality | Correct canonical ID ÷ predicted mappings on the labeled alias set | **≥ 0.90** precision, **≥ 0.85** recall |
| M3 | Matching quality | NDCG@10 per job, and Spearman ρ against the match gold | **NDCG@10 ≥ 0.80**, **ρ ≥ 0.60** |
| M4 | API completeness | Endpoint coverage vs. §8 by tests; OpenAPI schema validates | **100%** of §8 endpoints; 0 schema errors |
| M5 | Reliability | Small Locust run, `LLM_MODE=stub` | **0** 5xx responses at **~10** concurrent users |
| M6 | End-to-end latency | Wall-clock time for `POST /parse` on one resume, real Gemini | **p95 < 10 s**, p50 < 5 s; cache hit < 200 ms |
| M7 | Hallucination rate | Share of LLM-extracted fields whose evidence span cannot be found in the source | **≤ 5%** *(first estimate)* |
| M8 | Fairness | \|Δscore\| between counterfactual resume variants | **≤ 0.02** mean, **≤ 0.05** max *(first estimate)* |
| M9 | Fine-tuning gain | Fine-tuned vs. base embeddings on the test split | **≥ +2 pts** normalization recall; NDCG not lower *(first estimate)* |
| M10 | Search quality | Precision@10 on a 30-query gold set | **≥ 0.70** *(first estimate)* |

A "success" for M5 is any 2xx response, including a `partial` result. M7–M10 are first estimates. ADR-0003 allows one adjustment each, by ADR, after their first measurement.

---

## 3. Technology decisions

| Concern | Choice | Why |
|---|---|---|
| Language | **Python 3.12** | Best ecosystem for NLP and ML. |
| Package manager | **uv** | Fast, lockfile, same behaviour on Windows, Linux and Docker. |
| Orchestration | **LangGraph** | Explicit state graph, conditional edges for degradation, tool-calling nodes for F1, and loops for F3's critique cycle. |
| LLM | **Google Gemini free tier** via `google-genai`, model from `LLM_MODEL` | Free; structured JSON output validated with Pydantic. See §3.1. |
| Embeddings | **sentence-transformers** `all-MiniLM-L6-v2` (384-d), fine-tuned for F5 | Local and fast on CPU; no per-call cost. |
| Vector DB | **ChromaDB** (server mode) | Simple, open source, metadata filters; behind a `VectorStore` protocol. |
| Relational DB | **PostgreSQL 16**, SQLAlchemy 2.0 (async), Alembic | Taxonomy, candidates, jobs, matches, batches, agent runs. |
| Cache | **Redis 7** | Parse, JD and LLM-response caches keyed by content hash + `PIPELINE_VERSION`. |
| Background work | FastAPI **`BackgroundTasks`** | Batches of ≤ 20 files don't need a broker and worker pool (D14). |
| API | **FastAPI** + Pydantic v2; **slowapi** | Automatic OpenAPI; request validation; per-IP limits in a few lines. |
| PDF | **PyMuPDF** | Text blocks with bounding boxes and fonts for column ordering; built-in table finder. |
| DOCX | **python-docx** | Paragraphs, tables, styles; text boxes through XML. |
| Text utilities | **rapidfuzz**, **dateparser**, **phonenumbers** | Alias lookup, evidence alignment (F2), dates, phones. |
| Retries | **tenacity** | Declarative retry and backoff. |
| Logs | **structlog** (JSON) + `agent_runs` table | Per-agent timings without a tracing stack. |
| Front end | **Next.js** (App Router, TypeScript), **Tailwind CSS**, `openapi-typescript`, react-pdf | Typed client from OpenAPI; evidence highlighting on the PDF. |
| Testing | **pytest**, pytest-asyncio, httpx; **Locust** for the small load test | |
| Quality | **ruff**, **mypy** (strict, pinned < 2), pre-commit, **GitHub Actions** | CI runs lint, types, unit tests and the eval gate (F5). |
| Deployment | **Docker Compose** locally; backend on a small VM or container host, frontend on Vercel | |

### 3.1 LLM usage policy

The LLM is used **only where rules cannot work**. That keeps us within the latency budget and the free-tier quota, and lets the system degrade gracefully.

| Use | Where | Call pattern |
|---|---|---|
| Structured resume extraction | Parsing Agent | **One call per resume**, schema-constrained JSON with an `evidence` span per field |
| Disambiguating unresolved skills | Normalization Agent | **One batched call per resume**, only for skills rules and embeddings couldn't resolve |
| Parsing job descriptions | Matching Agent | One call per JD, cached by content hash |
| Query planning | Talent Search agent (F1) | One call per query, cached by query hash |
| Generation and critique | Career Coach agent (F3) | One generate and one critique call per round, at most 3 rounds; cached per (candidate, job, version) |

**Rules for every LLM call:**

- Every call goes through `llm/client.py` (`get_llm()`). `GeminiLLM` applies:
  - the model from `LLM_MODEL`, with `temperature=0` for extraction
  - a timeout (`LLM_TIMEOUT_S`) and tenacity retries on 429, 5xx and connection errors
  - a per-process concurrency semaphore (`LLM_MAX_CONCURRENCY`)
  - token and latency logging from `usage_metadata`
- A 429 that survives the retries raises `LLMQuotaExceeded`. Agents then degrade to rules-only output (`partial`). There is no automatic fallback model and no cross-process quota counter (D17).
- Prompts are static files in `llm/prompts/`, with the changing input at the end.
- `response_json_schema` can drop `Field(description=...)` on nested models, so important field guidance also goes in the prompt text. Responses are always validated with Pydantic.
- `LLM_MODE`: `real` (`GeminiLLM`; falls back to `fake` without a key), `fake` (recorded fixtures) or `stub` (fixtures plus simulated latency, for load tests).
- **All unit tests use `FakeLLM`.** Only tests marked `llm` call the real API.
- **Data use:** Google may use free-tier prompts. Only synthetic or consented resumes go to the free tier. The demo shows a warning on upload and leads with sample resumes (§9.2).

---

## 4. System architecture

### 4.1 Container view

```
 ┌──────────────────────┐        ┌───────────────────────────────────────────────┐
 │  Next.js web app     │  HTTPS │  api: FastAPI (/api/v1, OpenAPI, slowapi)     │
 │  (Vercel)            │ ─────▶ │                                               │
 └──────────────────────┘        │  LangGraph pipeline                           │
                                 │   ingest → parse → verify → normalize         │
                                 │          → [blind redact] → match → persist   │
                                 │  Talent Search agent  (tool calling)          │
                                 │  Career Coach agent   (generate→critique)     │
                                 │  BackgroundTasks → batch processing           │
                                 └───────┬──────────────┬──────────────┬─────────┘
                                         ▼              ▼              ▼
                                  postgres:16       chroma          redis:7
                                  taxonomy,         skills,         parse / JD /
                                  candidates, jobs, candidates      LLM caches
                                  matches, batches,
                                  agent_runs
                                         │
                       Gemini API (external) · sentence-transformers (in-process)
```

Docker Compose runs four services: `api`, `postgres`, `redis` and `chroma`. The web app runs separately (`web/`, `npm run dev` locally, Vercel for the demo).

### 4.2 Pipeline (LangGraph state machine)

```
 START
   │
   ▼
 ingest ──(bad file)──▶ fail_fast ──▶ END            (422: no pipeline run)
   │
   ▼
 parse ──(error after retries)──▶ record_error ─┐
   │                                            │  nothing usable → status "failed"
   ▼                                            ▼
 verify (F2: evidence alignment; never fails the run)
   │
   ▼
 normalize ──(error)──▶ record_error ──▶ persist (raw skills kept, status "partial")
   │
   ▼
 match? ──(no job given)──▶ persist
   │ (job given)
   ▼
 blind? ──(blind=true)──▶ redact (F4) ─┐
   │                                   ▼
   ▼◀──────────────────────────────────┘
 match ──(error)──▶ record_error ──▶ persist (profile kept, status "partial")
   │
   ▼
 persist ──▶ END
```

**Graph state** (`PipelineState`, Pydantic):

```
trace_id, batch_item_id?, candidate_id?, input_meta{filename, mime, sha256, bytes},
raw_document?, parsed_resume?, skill_profile?, match_result?, blind: bool,
agent_runs: list[AgentRun], errors: list[AgentError], status: ok|partial|failed
```

**Graceful degradation:**

| Failing agent | What is still returned | Status |
|---|---|---|
| Parsing: LLM step fails or quota exhausted | Rule-based extraction (contact, sections, lexicon skills) | `partial` |
| Parsing: everything fails | Nothing usable | `failed` (422 or 500 with a problem body) |
| Verify | Fields left `verified: null`, confidence unchanged | unchanged |
| Normalization | Parsed resume plus raw skill strings | `partial` |
| Matching | Parsed resume and profile, `match_result: null` | `partial` |

Each node runs inside `run_agent()`. It applies a per-agent timeout and tenacity retries (3 attempts, exponential backoff with jitter, only on `retryable` errors), and records an `AgentRun` (start, latency, attempts, quality, error) per attempt.

### 4.3 Concurrency

- The API is async. CPU-heavy work (PDF layout, embedding) runs in a bounded thread pool so it doesn't block the event loop.
- The embedding model loads **once per process** and is warmed at startup.
- Batches run in FastAPI `BackgroundTasks` inside the API process, at most `MAX_BATCH_FILES` (20) files per batch, processed with bounded concurrency. Progress lives in `batch_jobs` / `batch_items`. On startup, items left `running` by a restart are marked `failed` so the client can resubmit.
- LLM calls are capped per process by `LLM_MAX_CONCURRENCY`.

### 4.4 Caching

| Cache | Key | TTL | Purpose |
|---|---|---|---|
| Parse result | `parse:{sha256(file)}:{PIPELINE_VERSION}` | 7 days | Re-uploads and demo samples return instantly |
| JD parse | `jd:{sha256(text)}:{PIPELINE_VERSION}` | 7 days | No repeated JD extraction |
| Search plan (F1) | `search:{sha256(query)}:{PIPELINE_VERSION}` | 1 day | Repeat queries cost no quota |
| Coach output (F3) | `coach:{candidate_id}:{job_id}:{PIPELINE_VERSION}` | 7 days | Repeat requests cost no quota |
| Alias lookup | In-process dict, rebuilt when `taxonomy_version` changes | n/a | Fast normalization |
| Embeddings | Chroma, keyed by `skill_id` / `candidate_id` | permanent | Computed once per taxonomy or pipeline version |

Bump `PIPELINE_VERSION` whenever parser, normalizer or embedding-model output changes.

---

## 5. Agent protocol

Inside LangGraph, agents share `PipelineState` and return a common result type. This is the "shared message protocol" from the brief, without the cross-process envelope v1 needed for Celery (D13).

```python
class AgentResult(BaseModel):
    status: Literal["ok", "partial", "failed"]
    data: dict | None
    quality: QualityScore  # 0..1, with a breakdown
    latency_ms: int
    warnings: list[str] = []


class AgentError(BaseModel):
    agent: AgentName  # "parser" | "verifier" | "normalizer" | "matcher" | "search" | "coach"
    code: str  # e.g. "llm_timeout", "unsupported_layout"
    message: str
    retryable: bool
    attempt: int
```

Step 4.6 simplifies `core/schemas/messages.py` to this shape. It drops `message_id`, `parent_id` and the `heartbeat` type, and keeps `trace_id` on the state. Payload schemas are versioned (`schema_version`) and live in `core/schemas/`. The API returns the same models.

**Quality scores** (returned in `meta.quality`):

- **Parser:** the weighted mean of field confidences, with a penalty for missing core sections and for unverified fields.
- **Normalizer:** the share of skills mapped with confidence ≥ 0.8, and the share left unrecognized.
- **Matcher:** the share of job requirements that could be evaluated, and the margin between score and threshold.

---

## 6. Agent designs

### 6.1 Parsing Agent

**Input:** file bytes. **Output:** `ParsedResume`.

```
bytes ─▶ detect type ─▶ extractor ─▶ LayoutDocument ─▶ section detector ─▶ rule extractors
      ─▶ LLM structured extraction ─▶ evidence verifier (F2) ─▶ merge & validate ─▶ ParsedResume
```

1. **Type detection** from leading bytes: `%PDF` is PDF; a ZIP containing `word/document.xml` is DOCX; anything that decodes as UTF-8 or Latin-1 is text. Limits: 10 MB, 20 PDF pages.
2. **Extraction to `LayoutDocument`**, a list of `Block{text, page, bbox, font_size, bold, kind: paragraph|table|list}`.
   - **PDF:** PyMuPDF `page.get_text("dict")`. **Column ordering** groups blocks by their x-position into columns (a full-width block separates bands), then reads column by column, top to bottom. Tables come from PyMuPDF `find_tables()`. A low text-to-page-area ratio returns `unsupported_content`.
   - **DOCX:** body paragraphs and tables in document order, text boxes (`w:txbxContent`) through XML, heading styles as a signal.
   - **TXT:** paragraphs; uppercase lines or lines ending in a colon are candidate headers.
3. **Section detection** labels blocks as `contact | summary | experience | education | skills | certifications | projects | other`. It uses a header lexicon (`config/section_lexicon.yaml`), typography (larger or bold text, short lines, all caps) and position (contact info at the top or in a sidebar).
4. **Rule extractors** (deterministic, run first): email; phone (`phonenumbers`); URLs (LinkedIn, GitHub, portfolio); date ranges normalized to `YYYY-MM` with `is_current`; candidate skills from n-gram lookup against the alias index.
5. **LLM structured extraction:** one Gemini call over the section-labeled text, with the rule hints. The output is a `ResumeExtraction`. Every field carries `confidence` and `evidence`, a short verbatim span of the source text.
6. **Evidence verifier (F2):** each evidence span is aligned to the source text with rapidfuzz `partial_ratio`.
   - At **≥ 90** the field is `verified: true`.
   - Otherwise it is `verified: false`, and its confidence is multiplied by 0.5.
   - The share of unverified fields is the hallucination rate (M7).
   - The UI flags unverified fields and highlights verified spans on the document.
7. **Merge and validate:** rules win on contact fields; the LLM wins on structured entities. Dates must be in order, emails valid, and each role gets `duration_months`. `meta.field_sources` records `rules | llm | merged`.

**`ParsedResume` (abridged):**

```
personal: {name, email, phone, location{city, region, country}, links[]}
summary?
experience[]: {company, title, location?, start, end?, is_current, duration_months, responsibilities[], skills_mentioned[]}
education[]: {institution, degree, field, start?, end?}
skills[]: {raw, category_hint: technical|soft|unknown, evidence}
certifications[]: {name, issuer?}
projects[]: {name, description, technologies[], url?}
every LLM field: {value, confidence, evidence, verified}
meta: {layout: single|multi|table|creative, pages, confidence, field_sources, unverified_count}
```

### 6.2 Skill Normalization Agent

**Input:** `ParsedResume`. **Output:** `SkillProfile`, a list of canonical skills with proficiency, plus inferred and unrecognized skills.

**Taxonomy** (built in Phase 1; ADR-0001):
- 4 levels: **Domain → Category → Subcategory → Skill**.
- 9,642 skills and 15,122 aliases, with `ambiguous` flags.
- Implication rules, e.g. `{TensorFlow, PyTorch, Keras} ≥ 1 → Deep Learning (0.8)`.
- `related` edges, e.g. `Docker → Kubernetes`.

**Cascade** per raw skill string. The first confident step wins:

| Step | Method | Accept when |
|---|---|---|
| 0 | Clean: lowercase, strip versions, unify punctuation, split lists ("AWS/GCP") | n/a |
| 1 | Exact alias lookup | match → confidence 1.0 (ambiguous aliases go to step 4 when context exists) |
| 2 | Fuzzy match (rapidfuzz `token_sort_ratio`) | score ≥ 92 and a unique top hit |
| 3 | Embedding nearest neighbour in Chroma `skills` (fine-tuned model, F5) | cosine ≥ 0.82 and margin over the 2nd ≥ 0.05 |
| 4 | Batched LLM disambiguation over the top-5 candidates, with resume context | model picks an ID with confidence ≥ 0.7 |
| 5 | Otherwise: **unrecognized**, listed in the profile and counted in `emerging_skills` | n/a |

**Hierarchy inference:** apply the implication rules, and add ancestors with `inferred: true` and confidence `rule_conf × min(child_conf)`. Inferred skills never outrank explicit evidence.

**Proficiency** (level 1–5, plus `years` and a one-line explanation), configured in `config/proficiency.yaml`:

| Feature | Effect |
|---|---|
| `years_used`: summed durations of roles that mention the skill, overlaps merged | 0–2 y → 2, 2–5 y → 3, 5–8 y → 4, 8+ y → 5 (base) |
| Qualifier wording in the evidence ("expert in", "led" vs. "familiar with", "basic") | ±1 |
| Listed only in the skills section, with no supporting evidence | capped at 2 |

**Fine-tuned embeddings (F5):**
- **Training:** fine-tune `all-MiniLM-L6-v2` with `MultipleNegativesRankingLoss` on (alias, canonical name) pairs. The split is **by skill**, so test skills are never seen in training.
- **Publishing:** push the model to the Hugging Face Hub, pin its revision in `EMBEDDING_MODEL`, re-index Chroma and bump `PIPELINE_VERSION`.
- **Where it runs:** in Docker or Colab. torch can't load natively on the dev machine.
- **Acceptance:** the before/after table (M9) is published.

### 6.3 Semantic Matching Agent

**Input:** a `SkillProfile` plus a job (text, or a stored `job_id`). **Output:** `MatchResult`.

1. **Job parsing:** one cached LLM call extracts `JobRequirements`:
   - required and nice-to-have skills, each with `importance` (1–5) and an optional `min_years`
   - seniority
   - role family

   The skills are normalized with the same Normalization Agent, so both sides share canonical IDs.
2. **Per-requirement credit:** for each requirement `r`, take the best candidate skill `c`:
   - exact ID: 1.0
   - `c` is a descendant of `r`: 0.9
   - ancestor, or sibling in the same subcategory: 0.6
   - else embedding cosine if ≥ 0.55, otherwise 0

   `depth = min(1, years / r.min_years)` (or proficiency-based if `min_years` is unset), and `credit_r = sim × (0.6 + 0.4 × depth)`.
3. **Skill score:** `S_skill = Σ w_r·credit_r / Σ w_r`, with `w_r = importance_r × (1.0 if required else λ_nice)` and λ_nice = 0.35.
4. **Experience score:** `S_exp = min(1, relevant_years / years_for_seniority)`.
5. **Final score:** `score = α·S_skill + β·S_exp − penalty`.
   - Defaults: α 0.70, β 0.30.
   - Penalty: 0.1 per missing required skill with importance ≥ 4, then clamped to [0, 1].
   - α and β are tuned on train to maximize NDCG@10 (`config/matching.yaml`).
6. **Threshold:** `is_match = score ≥ threshold`. Presets are `precision` 0.75, `balanced` 0.60 and `recall` 0.45, calibrated on val; a custom value is also accepted.
7. **Gap analysis:** each unmet requirement lists the missing skill, the current and required level, and **upskilling hints**: skills the candidate already has that link to the gap through `related` or sibling edges ("you know Docker, so learn Kubernetes next").
8. **Explainability:** each requirement's breakdown shows the matched skill, the match type, the depth and the credit. The UI renders this as the "why this score" view.

**Blind screening (F4):** with `blind=true`, a redaction step runs before matching. It removes:
- name and contact details, and photo references
- gendered words and pronouns
- age signals: graduation and birth years, and "N years old"
- institution names

Durations stay, because they are computed before redaction. The matcher never sees protected attributes in either mode. Blind mode removes the proxies a human reviewer would see, and the fairness audit (§10.2) checks the scores.

### 6.4 Talent Search agent (F1)

**Input:** a plain-English query, e.g. *"backend engineers with 3+ years of Python and some Kubernetes, ideally fintech"*. **Output:** ranked candidates, each with a reason and evidence citations.

1. **Planner** (one cached LLM call): turns the query into a `SearchPlan`: must and should skills (normalized to canonical IDs through the Normalization Agent), minimum years, domain or industry, and seniority.
2. **Tool-calling loop** (LangGraph `ToolNode`, at most 4 tool rounds). The agent can call:
   - `search_skills(text)`: Chroma `skills`, to resolve vague terms
   - `filter_candidates(skill_ids, min_years, domain)`: a SQL filter over `candidate_skills`
   - `semantic_candidates(text, k)`: Chroma `candidates` (summary + skills embedding)
   - `match_candidate(candidate_id, plan)`: the Matching Agent's scorer against the plan as a synthetic job
3. **Re-rank and explain:** results are merged and ranked by match score. Each one cites the evidence spans that satisfied the must-have skills.
4. **Degradation:** with no LLM, a keyword-to-alias parser builds the plan and the tools run directly (`partial`).

Evaluation: a 30-query gold set built from the profiles' ground truth, scored with precision@10 (M10).

### 6.5 Career Coach agent (F3)

**Input:** a candidate and a `MatchResult`. **Output:** `CoachReport`.

`CoachReport` has three parts:
- a learning plan for the gaps, ordered by taxonomy `related` / prerequisite edges
- 5 interview questions aimed at the weakest requirements
- up to 5 resume-bullet rewrites that rephrase **existing** evidence only

**Loop** (a LangGraph subgraph):

```
generate ─▶ critic ─(all claims supported)──▶ END
              │
              └─(unsupported claims)─▶ revise ─▶ critic   (at most 2 revisions)
```

The **critic** works in two stages:
- **Deterministic first:** every skill named in a bullet rewrite must be in the profile with evidence, and every learning-plan skill must exist in the taxonomy.
- **Then one LLM check** for invented experience, employers, numbers or dates.

Anything still unsupported after 2 revisions is dropped, and the report lists what was removed. Acceptance: a 20-case adversarial set where the generator is pushed to invent experience. The critic must leave **0** unsupported claims in the final output.

---

## 7. Data model

### 7.1 PostgreSQL (after migration 0002)

```
skills(id PK, slug UNIQUE, name, type, level SMALLINT, parent_id FK→skills, description, taxonomy_version, created_at)
skill_aliases(id PK, skill_id FK, alias, alias_normalized UNIQUE, ambiguous, source)
skill_implications(id PK, antecedent_ids INT[], consequent_id FK, min_count, confidence)
skill_relations(skill_id FK, related_id FK, kind: related|prerequisite, weight)
emerging_skills(id PK, normalized_text UNIQUE, occurrences, example_contexts JSONB)      -- unrecognized-skill store

candidates(id UUID PK, file_sha256, parsed JSONB, quality REAL, pipeline_version, created_at)
candidate_skills(candidate_id FK, skill_id FK, proficiency SMALLINT, years REAL, inferred BOOL, confidence REAL, evidence JSONB, PK(candidate_id, skill_id))
jobs(id UUID PK, title, raw_text, requirements JSONB, text_sha256, created_at)
matches(id UUID PK, candidate_id FK, job_id FK, score REAL, threshold REAL, is_match BOOL, breakdown JSONB, gaps JSONB, created_at)

batch_jobs(id UUID PK, status: queued|running|completed|completed_with_errors|failed, total, succeeded, failed, partial, created_at, finished_at)
batch_items(id UUID PK, batch_job_id FK, filename, status, candidate_id FK?, error JSONB)

agent_runs(id PK, trace_id UUID, agent, attempt, status, latency_ms, quality REAL, error_code, started_at)
```

Later milestones add their own migrations: `matches.blind` (Step 4.8), and `demo` flags on candidates and jobs (Step 7.4).

### 7.2 ChromaDB collections

| Collection | ID | Document | Metadata |
|---|---|---|---|
| `skills` | `skill_id` | Canonical name, top aliases, description | `type`, `level`, `parent_id`, `taxonomy_version` |
| `candidates` (Step 6.1) | `candidate_id` | Summary + canonical skill names + titles | `pipeline_version`, `industry`, `total_years` |

---

## 8. API design

**Base path:** `/api/v1`. **Auth:** the `X-API-Key` header on write endpoints, compared with `API_KEY` (a blank `API_KEY` disables auth for local development). **Docs:** Swagger UI at `/docs`, ReDoc at `/redoc`, schema at `/openapi.json`.

| Method | Path | Description | Mode |
|---|---|---|---|
| POST | `/parse` | Upload one resume. Returns `candidate_id`, the parsed resume, the skill profile and `meta`. `?include=trace` | Sync |
| POST | `/parse/batch` | Upload up to 20 files. Returns `202` with `batch_job_id` | Background |
| GET | `/jobs/{batch_job_id}` | Batch status, per-item status and results | n/a |
| GET | `/candidates/{id}` | Full parsed candidate | n/a |
| GET | `/candidates/{id}/skills` | Skill profile; filters `type`, `min_proficiency`, `include_inferred` | n/a |
| POST | `/match` | `{candidate_id, job: {title, description} \| job_id, threshold? \| preset?}` → `MatchResult`; `?blind=true` | Sync |
| POST | `/match/rank` | Rank candidates (all, or a given list) for one job; `?blind=true` | Sync |
| POST | `/search` | `{query, limit?}` → ranked candidates with reasons (F1) | Sync |
| POST | `/coach` | `{candidate_id, job_id}` → `CoachReport` (F3) | Sync |
| GET | `/skills/taxonomy` | Browse the tree: `parent_id`, `depth`, `limit`/`offset` | n/a |
| GET | `/skills/search` | `?q=`: alias, fuzzy and semantic search | n/a |
| GET | `/skills/{id}` | Ancestors, children, aliases, related skills | n/a |
| GET | `/health` | Liveness. No auth | n/a |
| GET | `/ready` | DB, Redis, Chroma and model loaded. No auth | n/a |

### 8.1 Cross-cutting behaviour

- **Rate limiting:** slowapi, per client IP, `RATE_LIMIT_PER_MIN` (default 60). LLM-heavy endpoints (`/parse`, `/search`, `/coach`) get a lower limit. Over the limit, the response is `429` with `Retry-After`.
- **Validation:** Pydantic request models. Uploads are checked by magic bytes, 10 MB max, 20 files per batch.
- **Errors:** RFC 7807 `application/problem+json`, rendered by `api/problems.py` from `TalentGraphError` subclasses (`code`, `http_status`, `retryable`):

  ```json
  {"type": "https://talentgraph.dev/errors/unsupported_file_type", "title": "Unsupported file type",
   "status": 415, "detail": "Detected image/png; expected PDF, DOCX or TXT.",
   "instance": "/api/v1/parse", "trace_id": "…", "errors": []}
  ```

- **Pagination:** `?limit=&offset=`.
- **Response envelope (pipeline endpoints):** `{data, meta: {status, trace_id, pipeline_version, latency_ms, quality, warnings[], trace?}}`. `trace` is the per-agent timeline from `agent_runs`.
- **CORS:** allows the web app's origin (`WEB_ORIGIN`, added in Step 5.1).
- **Examples:** `examples/` holds a cURL walkthrough and one Python script covering every endpoint. There are no SDK packages (D13).

---

## 9. Web app and live demo

### 9.1 Pages (Next.js, `web/`)

| Page | What it shows | API |
|---|---|---|
| **Upload & Profile** | Drag-and-drop or a sample resume. Parsed fields with verified/unverified badges, evidence highlighted on the rendered document, skill chips with taxonomy path, proficiency, and inferred and unrecognized skills, plus the agent timeline | `/parse?include=trace`, `/candidates/{id}/skills` |
| **Match** | Paste a JD or pick a sample. Preset selector and blind toggle. Score gauge, the **"why this score"** requirement table, gaps with upskilling hints | `/match` |
| **Recruiter Ranking** | Pick a job and get a ranked candidate list with scores and top gaps; blind toggle | `/match/rank` |
| **Talent Search** | Natural-language query box and ranked results with reasons and citations | `/search` |
| **Coach** | Learning plan, interview questions and bullet rewrites, with what the critic removed | `/coach` |
| **Taxonomy** | Tree browser and skill search | `/skills/*` |
| **Evaluation** | M1–M10 tables and charts, PR curve, fairness audit, fine-tuning before/after; read from `reports/` JSON at build time | static |
| **About** | Architecture diagram, stack, links to the repo and ADRs | static |

The typed API client is generated with `openapi-typescript` from `/openapi.json`. The pages are responsive, with light and dark themes.

### 9.2 Demo mode

- `scripts/seed_demo.py` loads about 30 sample resumes and 10 sample JDs. It then runs the pipeline once, so parse, match, search and coach results are cached in Redis and stored in Postgres.
- The UI leads with the samples. Uploads show a warning: *free-tier LLM; do not upload real personal data*. The upload size is capped, and uploaded files are deleted after parsing.
- If the daily Gemini quota runs out, uploads still work in rules-only `partial` mode, and the samples keep working from the cache.

### 9.3 Hosting

- **Backend:** the `api` image (embedding model baked in, about 1.5–2 GB RAM) with Postgres, Redis and Chroma on one small VM or container host.
- **Frontend:** Vercel, with `NEXT_PUBLIC_API_URL` pointing at the backend and CORS set to match.
- **Secrets:** the API key and the Gemini key are held server-side. The web app calls the API through a Next.js route handler, so the key never reaches the browser.

---

## 10. Datasets and evaluation

### 10.1 Datasets (built in Phase 1; see `data/README.md`)

| Dataset | Size | Source |
|---|---|---|
| Skill taxonomy | 9,642 skills, 15,122 aliases | O\*NET 31.0 + Wikidata alt-labels + a curated layer (ADR-0001) |
| Synthetic resumes | 560 (11 industries, 6 templates; PDF 42%, DOCX 41%, TXT 17%) | Ground-truth profile first, then rendered; template text, no LLM (ADR-0002) |
| Job descriptions | 120 across 9 role families | Generated with ground-truth `JobRequirements` |
| Normalization gold | 1,200 pairs, 25% hard cases | `scripts/build_normalization_gold.py` |
| Match gold | 2,400 pairs graded 0–4 | Rubric labeler (ADR-0002); **must be re-validated before Milestone 4 sign-off** |
| Search gold (Step 6.3) | 30 queries | Built from profile ground truth |
| Coach adversarial set (Step 6.5) | 20 cases | Hand-written |
| Fairness variants (Step 4.10) | Counterfactual copies of test resumes | Generated by `eval/fairness.py` |
| Reworded resumes (Step 2.14) | A subset of val/test, rewritten | Gemini rewrites summaries and bullets of synthetic profiles; ground truth kept (ADR-0004 A) |
| Real-resume check set (Step 2.15) | 10–20 | Consented resumes, hand-labeled; **private, never committed** (ADR-0004 B) |
| External skill benchmark (Step 3.11) | TechWolf `skill-extraction-{techwolf,tech,house}` | CC BY 4.0; ESCO-labeled skill spans, crosswalked to our slugs by exact name/alias (ADR-0004 D) |
| Real job postings (Steps 3.11, 4.11) | ~100 USAJOBS postings; `data_jobs` skill lists | USAJOBS terms (credit, unmodified; eval only until reuse is confirmed); Apache-2.0 (ADR-0004 E) |

**Splits:** 70/15/15 train/val/test, stratified by industry and template. **The test split is never used for tuning.**

**Primary vs. supplementary data (ADR-0004):** pass or fail on M1–M10 is decided on the synthetic test split. The reworded, real, external and USAJOBS sets are reported next to M1, M2 and M9 as "reworded / real / external" figures on the evaluation page, with no targets and never used for tuning. External data is credited in `data/external/ATTRIBUTION.md`.

### 10.2 Evaluation harness (`eval/`)

Each script writes JSON and Markdown to `reports/`, stamped with the time and git SHA. `reports/baseline/` and `reports/final/` are committed; the evaluation page reads `reports/final/`.

| Script | Measures | Metric |
|---|---|---|
| `eval/parsing.py` | Field-level P/R/F1 by field, template and format; list entities aligned in order; hallucination rate | M1, M7 |
| `eval/normalization.py` | Precision, recall, unrecognized rate, worst-error list; base vs. fine-tuned model | M2, M9 |
| `eval/matching.py` | NDCG@5/@10, Spearman/Kendall, threshold PR curve; base vs. fine-tuned model | M3, M9 |
| `eval/fairness.py` | Score deltas over counterfactual variants (names across gender and ethnicity, pronouns, graduation years), in normal and blind mode | M8 |
| `eval/search.py` | Precision@10 on the query gold set | M10 |
| `eval/coach.py` | Unsupported claims left after the critic on the adversarial set | F3 acceptance |
| `eval/latency.py` | Sequential parses: p50/p95/p99 and per-agent breakdown | M6 |
| `eval/load/locustfile.py` | ~10 users, mixed parse/match/search, `LLM_MODE=stub` | M5 |

**CI eval gate (F5):** a GitHub Actions job runs `eval/parsing.py`, `eval/normalization.py` and `eval/matching.py` on a fixed val subset with FakeLLM fixtures. It fails the build if a metric drops more than its tolerance below `reports/baseline/`.

---

## 11. Repository layout

```
TalentGraph/
├── CLAUDE.md  README.md  CHANGELOG.md (Milestone 8)
├── documents/              # idea.md, plan.md, ordered.md, project-plan-v2.md, archive/ (v1 docs)
├── pyproject.toml  uv.lock  .env.example  .pre-commit-config.yaml
├── docker-compose.yml  Dockerfile  alembic.ini  migrations/
├── config/                 # matching.yaml, normalization.yaml, proficiency.yaml, section_lexicon.yaml
├── src/talentgraph/
│   ├── __init__.py         # __version__, PIPELINE_VERSION
│   ├── config.py           # pydantic-settings; the only place that reads env vars
│   ├── core/               # schemas/, errors.py, ids.py
│   ├── llm/                # client.py, fake.py, prompts/
│   ├── embeddings/         # encoder.py, vector_store.py
│   ├── db/                 # models.py, session.py, repositories/
│   ├── agents/
│   │   ├── base.py         # Agent protocol, run_agent()
│   │   ├── parsing/        # detect, pdf, docx, text, layout, sections, rules, llm_extract, verify, agent
│   │   ├── normalization/  # clean, cascade, hierarchy, proficiency, emerging, agent
│   │   ├── matching/       # job_parser, scoring, thresholds, gaps, blind, agent
│   │   ├── search/         # planner, tools, agent (F1)
│   │   └── coach/          # generate, critic, agent (F3)
│   ├── orchestrator/       # state.py, graph.py, batch.py
│   ├── api/                # main.py, deps.py, auth.py, ratelimit.py, problems.py, routers/
│   └── observability/      # logging.py
├── web/                    # Next.js app (Milestone 7)
├── scripts/                # data generators, seed.py, seed_demo.py, finetune_embeddings.py, tune_matching.py, record_llm_fixtures.py
├── data/                   # taxonomy/, profiles/, resumes/ (not committed), jobs/, eval/
├── eval/                   # parsing, normalization, matching, fairness, search, coach, latency, load/
├── examples/               # cURL walkthrough, Python example
├── tests/                  # unit/, integration/, e2e/, fixtures/
├── docs/                   # decisions/ (ADRs), progress/, errors.md
└── reports/                # eval outputs (baseline/ and final/ committed)
```

---

## 12. Engineering conventions

- **Config:** all settings come from `talentgraph.config.Settings`. Never read `os.environ` elsewhere. `.env.example` lists every variable.
- **Schemas first:** every cross-component contract is a Pydantic model in `core/schemas`. API responses reuse them.
- **Determinism:** rule steps and scoring are pure functions, unit-tested without I/O. Randomness is seeded.
- **Test markers:** `unit` (default), `integration`, `e2e`, `llm` (real API; never in default CI) and `slow`. The default `pytest` run passes offline in under 60 s.
- **Coverage:** ≥ 80% line coverage on `src/talentgraph/agents` and `src/talentgraph/api`.
- **Versioning:** `PIPELINE_VERSION` changes when output semantics or the embedding model change; `taxonomy_version` when the taxonomy is reloaded. Both appear in API `meta`.
- **ADRs:** a decision that changes this plan gets an ADR in `docs/decisions/` and a row in §14.
- **Progress records:** when a milestone's exit criteria pass, write `docs/progress/milestone-NN.md` from the template in `ordered.md`.
- **Git:** the owner does all commits and pushes.

---

## 13. Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Gemini free-tier quota (RPM/RPD) | Demo, eval runs, F1 and F3 burn quota | Redis caches; demo mode with pre-computed samples; FakeLLM in CI; `stub` for load tests; degrade to rules on 429 |
| Free-tier data use (Google may use prompts) | Demo visitors upload real resumes | Upload warning; samples first; upload cap and deletion; a paid key before any real PII |
| Gemini model churn | Model IDs disappear | `LLM_MODEL` is config; check it at the start of each milestone |
| LLM latency pushes `/parse` over 10 s | M6 fails | One extraction call, `temperature=0`, static prompt prefix, cache hits in ms, degrade after `LLM_TIMEOUT_S` |
| Hosting a CPU embedding model | Free hosts lack ~2 GB RAM | Small paid VM or container host; model baked into the image |
| Windows Application Control blocks torch `_C` and mypy 2 DLLs | Encoder, seeding and fine-tuning can't run natively | Run them in the api container or Colab; mypy pinned < 2; unit tests never load torch |
| Synthetic data too clean | Inflated M1–M3 | Template variety and noise (Phase 1); a few consented real resumes for qualitative checks; limitation stated on the eval page |
| Match gold from a rubric labeler (ADR-0002) | M3 is circular with skill overlap | LLM judge or human κ before Milestone 4 sign-off; report which one |
| Hallucinated extraction or coaching | Wrong profiles, invented experience | F2 verifier (M7) and F3 critic; both measured and published |
| Bias in scoring | Unfair rankings in a regulated domain | No protected attributes as features; blind mode; counterfactual audit (M8) |
| Fine-tuning overfits the aliases | Gains on train only | Split by skill; report on the test split only |
| BackgroundTasks lose work on restart | Batch items stuck | Stale `running` items marked `failed` on startup; batches capped at 20 |
| Scope creep from the five features | Project never ships | Strict milestone order; F1 and F3 come after the core is measured |
| Ambiguous skills ("Go", "R", "Swift", "Spring") | Normalization errors | `ambiguous` aliases always route to context-aware LLM disambiguation |
| PII in logs | Compliance | Log IDs and hashes only; `agent_runs` holds no payloads; uploads deleted after processing |

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
| D13 | 2026-10-13 | **Portfolio re-scope:** add a Next.js app, a live demo and five AI features (F1–F5); remove SDKs, webhooks, tracing/metrics stack, key scopes, idempotency, cursor pagination and the parsing/matching extras listed in ADR-0003; 12 phases become 8 milestones *(ADR-0003)* | The audience is hiring managers for AI roles; a visible, measured AI system beats unseen infrastructure |
| D14 | 2026-10-13 | FastAPI **BackgroundTasks** for batches, ≤ 20 files *(supersedes D2 and D8; ADR-0003)* | One process is enough for a demo; removes the worker, broker queues and Flower |
| D15 | 2026-10-13 | **Next.js** web app and hosted demo *(supersedes the v1 "no front-end UI" scope; ADR-0003)* | Reviewers must see the system without cloning it |
| D16 | 2026-10-13 | M5 becomes 0 5xx at ~10 concurrent users with `LLM_MODE=stub` *(supersedes D10 in part; ADR-0003)* | No worker pool; the demo has one user at a time |
| D17 | 2026-10-13 | One Gemini model (`LLM_MODEL`); 429 after retries degrades to rules; no cross-process RPM/RPD limiter; slowapi for API limits; Redis kept as cache only *(supersedes D9 in part; ADR-0003)* | Single process, cached demo; the removed machinery added code without visible value |
| D18 | 2026-10-13 | New metrics **M7–M10** with first-estimate targets *(ADR-0003)* | F2, F4, F5 and F1 need measurable acceptance criteria |
| D19 | 2026-10-13 | Keep the synthetic corpus as the primary dataset; add LLM-reworded resumes, a consented real-resume check set, the TechWolf ESCO skill benchmark (CC BY 4.0) and real job postings (USAJOBS; `data_jobs`, Apache-2.0) as report-only supplements *(ADR-0004)* | Public resume data lacks field labels, carries PII the free tier must not see, and is often scraped; targeted additions fix the synthetic set's known weaknesses |
| D20 | 2026-10-13 | The LLM returns **line references** for long text (summary, bullets, project descriptions); short fields keep verbatim evidence and alignment. M7 counts short fields plus invalid line references; target unchanged *(proposed; ADR-0005)* | Fewer output tokens for the 2-F latency budget; copied long text drifts, while referenced text is the source by construction |
| D21 | 2026-10-15 | **Compact LLM output** for resume extraction: line *ranges*, dates only as verbatim text (rules normalize), no model-reported confidence (fixed prior, halved if unverified), skills-section items not repeated, `skills_mentioned` derived, minified JSON; prompt frozen for daily free-tier recording *(extends D20; ADR-0005 amendment)* | Latency is output size (~90 tok/s, no thinking tokens): 1,225 → 616 tokens, 11.0 → 6.8 s on the same resume; the model's confidence was a constant 0.95 |

Add new rows here. Never edit old rows; add a row that supersedes them instead.

---

## 15. Glossary

- **Canonical skill:** a node in the taxonomy, with a stable `slug` and ID.
- **Alias:** a surface form that maps to a canonical skill (`k8s` → `kubernetes`).
- **Implication rule:** evidence of some skills implies another (TensorFlow + PyTorch ⇒ Deep Learning).
- **Unrecognized skill:** a skill string that couldn't be mapped confidently. It is listed in the profile and counted in `emerging_skills`.
- **Evidence span:** a verbatim snippet of the resume that an LLM-extracted field cites. It is verified by alignment (F2).
- **Blind mode:** matching after identity and age signals are redacted (F4).
- **Partial result:** the pipeline completed, but at least one agent failed. The response contains everything the successful agents produced.
- **Pipeline version:** a constant for the semantics of parser, normalizer and embedding output. It is part of every cache key.
