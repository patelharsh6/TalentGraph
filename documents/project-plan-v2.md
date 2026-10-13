# TalentGraph v2: Portfolio Project Plan

> **Status:** Approved by the owner on 2026-10-13. Recorded as [ADR-0003](../docs/decisions/ADR-0003-portfolio-rescope.md) and plan §14 D13–D18.
> **Relationship to other docs:** this is the one-page summary. The full design is [`plan.md`](plan.md) and the build order with exit criteria is [`ordered.md`](ordered.md); where they differ in detail, those two win. The v1 versions are in [`archive/`](archive/).

---

## 1. Executive Summary

### Goal
Rebuild TalentGraph as a **portfolio project for AI/ML engineering roles**. A reviewer should be able to open a live demo and, within 2–5 minutes, see a working multi-agent AI system with **measured** quality, **grounded** LLM output and **responsible-AI** safeguards. The original plan answered a challenge brief at enterprise depth. This version keeps the AI core and adds features that show modern AI-engineering skills. It drops the infrastructure work a reviewer never sees.

### Problem it solves
Applicant tracking systems match resumes by literal keywords. They miss obvious equivalents (`React.js` / `ReactJS` / `React`, `K8s` / `Kubernetes`), handle varied resume layouts badly, and give recruiters a score with no explanation. TalentGraph:

1. **parses** any PDF, DOCX or TXT resume into structured data, and every extracted field cites its source text;
2. **normalizes** skills to a 5,000+ skill taxonomy, infers implied skills and estimates proficiency;
3. **matches** candidates to jobs semantically, explains each score requirement by requirement, and lists skill gaps;
4. lets recruiters **search in plain English**, screen **blind** (without identity signals) and get **coaching output** (learning plan, interview questions);
5. publishes its own **evaluation metrics**, including hallucination rate and a fairness audit.

### What changed from v1
| Area | v1 | v2 |
|---|---|---|
| Audience | Challenge judges / enterprise integrators | Hiring managers for AI roles |
| Interface | Swagger UI only | **Next.js web app** + Swagger, plus a **hosted live demo** |
| Infrastructure | 7+ services (Celery, Flower, Jaeger, Prometheus…) | api, postgres, redis, chroma, plus the frontend |
| AI depth | 3 agents | 3 agents + **Career Coach agent**, **agentic NL search**, **grounding verifier**, **fine-tuned embeddings**, **fairness audit** |
| Process | 12 strict phases with heavy exit records | 8 milestones, each with metric-based exit criteria |

---

## 2. Core Architecture & Tech Stack

### 2.1 Architecture

```
 ┌──────────────────────┐        ┌───────────────────────────────────────────────┐
 │  Next.js web app     │  HTTPS │  FastAPI  (/api/v1, OpenAPI, slowapi limits)  │
 │  upload · profile ·  │ ─────▶ │                                               │
 │  match · rank ·      │        │  LangGraph pipeline                           │
 │  search · coach ·    │        │   ingest → parse → verify → normalize         │
 │  eval page           │        │          → [blind redact] → match → persist   │
 └──────────────────────┘        │                                               │
                                 │  LangGraph agents (separate graphs)           │
                                 │   • Talent Search agent (tool calling)        │
                                 │   • Career Coach agent (generate→critique)    │
                                 │                                               │
                                 │  FastAPI BackgroundTasks → batch processing   │
                                 └───────┬──────────────┬──────────────┬─────────┘
                                         │              │              │
                                  PostgreSQL 16     ChromaDB        Redis 7
                                  candidates, jobs, skill vectors,  parse / JD /
                                  taxonomy, batches candidate       LLM-response
                                  agent_runs        vectors         cache
                                         │
                                  Google Gemini (free tier) via llm/client.py
                                  sentence-transformers (fine-tuned MiniLM, CPU)
```

### 2.2 Pipeline and degradation
| Step | On failure | Result status |
|---|---|---|
| Parse: LLM step fails or quota exhausted | Rule-based output only (contact, sections, lexicon skills) | `partial` |
| Parse: everything fails | Error response | `failed` |
| Verify (grounding) | Fields left unverified, confidence lowered | `ok` / `partial` |
| Normalize | Raw skill strings returned | `partial` |
| Match | Profile returned, `match_result: null` | `partial` |

Each agent runs inside a `run_agent()` helper: timeout, up to 3 retries on retryable errors, and an `AgentRun` record (latency, attempts, quality score). `?include=trace` returns that timeline to the caller.

### 2.3 Tech stack (confirmed)
| Layer | Choice |
|---|---|
| Language / packaging | Python 3.12, **uv** |
| Frontend | **Next.js** (App Router, TypeScript) + **Tailwind CSS**; react-pdf for evidence highlighting |
| API | **FastAPI** + Pydantic v2, OpenAPI/Swagger/ReDoc, **slowapi** rate limiting, RFC 7807 errors |
| Background work | FastAPI `BackgroundTasks` (Celery removed) |
| Orchestration | **LangGraph**: main pipeline, tool-calling search agent, reflection-loop coach agent |
| LLM | **Google Gemini** free tier via `google-genai`; `FakeLLM` for tests, `stub` mode for load tests |
| Parsing | **PyMuPDF**, python-docx, rapidfuzz, dateparser, phonenumbers |
| Embeddings | **sentence-transformers** `all-MiniLM-L6-v2`, **fine-tuned** on taxonomy alias pairs; hosted on Hugging Face Hub |
| Vector DB | **ChromaDB** (collections: `skills`, `candidates`) |
| Relational DB | **PostgreSQL 16**, SQLAlchemy 2 (async), Alembic |
| Cache | **Redis 7**: parse, JD and LLM-response caches keyed by content hash + `PIPELINE_VERSION` |
| PII / fairness | Regex + spaCy NER redaction; counterfactual test harness |
| Logging | structlog (JSON) and the `agent_runs` table |
| Quality | pytest, ruff, mypy (strict, pinned < 2), pre-commit, **GitHub Actions** (tests + eval gate) |
| Deployment | Docker Compose locally. Demo: backend on a small VM / container host, frontend on Vercel |

### 2.4 Removed from v1
Celery + Flower · webhooks and `webhook_deliveries` · JS SDK and Python SDK packages · OpenTelemetry + Jaeger + Prometheus · Locust at 50 users · `docker-compose.prod.yml` + backup sidecar · emerging-skill review workflow and admin endpoints · API-key scopes and per-key data ownership · custom Redis sliding-window limiter · `Idempotency-Key` · cursor pagination · cross-process Gemini RPM/RPD limiter and automatic fallback-model switching · TF-IDF section classifier · k-means column detection · pdfplumber · city gazetteer · publications field and certification expiry/credential ID · 6-feature proficiency model · whole-profile semantic score, project-complexity signals, S/M/L effort estimates · Spectral lint / API-contract eval script · Hungarian alignment in the parsing eval · ZIP batch uploads · the 12-phase process · stretch goals other than embedding fine-tuning.

---

## 3. Feature Breakdown & Requirements

### 3.1 Core pipeline features

**C1. Resume parsing (Parsing Agent)**
- Inputs: PDF (text-based), DOCX, TXT; type detected from magic bytes; max 10 MB, 20 pages.
- PyMuPDF text blocks sorted by position (column-aware by x-position), plus a header-word lexicon for sections.
- Regex/phonenumbers for email, phone, links; dateparser for date ranges.
- **One Gemini call** per resume extracts: personal info, summary, experience, education, skills, projects, certifications (name, issuer). Every field carries `confidence` and `evidence`.
- Merge rule: regex wins for contact fields, LLM wins for structured entities.
- Scanned / image-only PDFs → `422 unsupported_content`.

**C2. Skill normalization (Normalization Agent)**
- Cascade: clean → exact alias → fuzzy (≥ 92, unique top hit) → embedding (cosine ≥ 0.82, margin ≥ 0.05) → one batched LLM disambiguation → **unrecognized**.
- Hierarchy inference from implication rules and ancestors (`inferred: true`).
- Proficiency 1–5 from **years used** plus **qualifier wording** ("expert in" / "familiar with"). A skill only listed in the skills section is capped at level 2.
- Unrecognized skills are listed in the profile (no admin review workflow).

**C3. Semantic matching (Matching Agent)**
- JD parsed by one cached Gemini call into required / nice-to-have skills (importance 1–5, optional min years), then normalized with C2.
- Per-requirement credit: exact 1.0 · candidate has a child skill 0.9 · ancestor/sibling 0.6 · else embedding cosine if ≥ 0.55 · scaled by years depth.
- Score = weighted skill credit (nice-to-have weight λ = 0.35) blended with a years-of-experience factor, minus a penalty for missing important required skills.
- Threshold presets: `precision` 0.75 · `balanced` 0.60 · `recall` 0.45, or a custom value.
- Gap analysis with upskilling hints from `related` / sibling edges ("you know Docker → learn Kubernetes").
- **Explainability:** per-requirement breakdown (matched skill, match type, depth, credit).

**C4. Orchestration**
- LangGraph state machine with graceful degradation (§2.2); `AgentResult` per agent (status, data, error, latency, quality). The full `AgentMessage` envelope is simplified.
- Batch: up to ~20 files per request, processed with BackgroundTasks; progress kept in `batch_jobs` / `batch_items`.

**C5. REST API** (`/api/v1`)
| Method | Path | Purpose |
|---|---|---|
| POST | `/parse` | Parse one resume (`?include=trace`) |
| POST | `/parse/batch` | Multi-file upload → `202` + `batch_job_id` |
| GET | `/jobs/{id}` | Batch progress and per-item results |
| GET | `/candidates/{id}` | Parsed candidate |
| GET | `/candidates/{id}/skills` | Skill profile (filters: type, min proficiency, inferred) |
| POST | `/match` | Candidate vs. JD → `MatchResult` (`?blind=true`) |
| POST | `/match/rank` | Rank candidates for one job (`?blind=true`) |
| POST | `/search` | **F1** natural-language talent search |
| POST | `/coach` | **F3** Career Coach output for a candidate + job |
| GET | `/skills/taxonomy` | Browse the tree (`parent_id`, `depth`, `limit`/`offset`) |
| GET | `/skills/search` | Alias + fuzzy + semantic skill search |
| GET | `/skills/{id}` | Skill detail: ancestors, children, aliases, related |
| GET | `/health`, `/ready` | Liveness / readiness (no auth) |

Cross-cutting: one API key (`X-API-Key`, from env) for write endpoints; slowapi per-IP limits; RFC 7807 errors; `limit`/`offset` pagination.

### 3.2 Portfolio presentation features

| ID | Feature | Requirements |
|---|---|---|
| P1 | **Next.js web app** | Pages: Upload & Profile · Match (JD paste, preset selector) · Recruiter Ranking · Talent Search · Coach · Taxonomy Browser · Evaluation. Responsive, light/dark. |
| P2 | **Hosted live demo** | Public URL; backend container with the embedding model baked in; frontend on Vercel. |
| P3 | **"Why this score" view** | Requirement-by-requirement table and visual bars from the C3 breakdown. |
| P4 | **Recruiter ranking** | One job → ranked candidate list with scores, top gaps, blind-mode toggle. |
| P5 | **Evaluation page** | M1–M9 results, charts, PR curve, fairness audit, before/after fine-tuning table; generated from `reports/` JSON. |
| P6 | **README** | Live link, demo GIF, architecture diagram, metrics table, "design decisions" section linking the ADRs. |
| P7 | **Demo mode** | One-click sample resumes and JDs with pre-cached results, so visitors don't spend Gemini quota. |

### 3.3 Advanced AI features

**F1. Natural-language talent search (agentic RAG)**
- Input: free text, e.g. *"Backend engineers with 3+ years of Python and some Kubernetes, ideally fintech."*
- An LLM planner produces a structured query (skills → canonical IDs, min years, domain, must/should).
- LangGraph tool-calling agent with tools `search_skills` (Chroma), `filter_candidates` (Postgres), `semantic_candidates` (Chroma `candidates` collection), `match_candidate` (C3).
- Output: ranked candidates, each with a reason and evidence citations. Planner output is cached by query hash.
- Requirement: a 30-query gold set for evaluation (M10).

**F2. Grounded extraction and hallucination check**
- Every LLM-extracted field must include an `evidence` span.
- A verifier node fuzzy-aligns each span to the source text (rapidfuzz, threshold ≥ 90). Fields that fail are marked `verified: false`, their confidence drops, and the UI flags them.
- UI highlights evidence spans on the rendered resume.
- New metric: hallucination rate (M7).

**F3. Career Coach Agent (fourth agent, reflection loop)**
- Input: candidate profile + match result.
- Generates a learning plan for the gaps (ordered by taxonomy `related` edges), 5 interview questions aimed at weak areas, and resume-bullet rewrites drawn only from existing evidence.
- A **critic** step checks every claim against resume evidence and the taxonomy and rejects invented experience. Up to 2 revise loops, then return what passes.
- Output cached by (candidate, job, pipeline version).

**F4. Blind screening and fairness audit**
- `blind=true` redacts name, contact details, photo references, gendered terms, age signals (graduation / birth years) and institution names before matching.
- Fairness harness in `eval/fairness.py`: counterfactual variants of the same resume (swapped names across gender/ethnicity, pronouns, graduation years). The match score must change by less than ε (M8).
- Results shown on the evaluation page.

**F5. Fine-tuned skill embeddings and CI eval gate**
- Fine-tune MiniLM on (alias, canonical) pairs from the train split with `MultipleNegativesRankingLoss`; publish the model on Hugging Face Hub; pin its revision in config.
- Before/after comparison: normalization recall and matching NDCG (M9).
- GitHub Actions job runs a reduced eval (FakeLLM fixtures, val subset) on each PR and **fails if M1–M3 regress** past a set tolerance.

### 3.4 Quality targets
| # | Metric | Target |
|---|---|---|
| M1 | Parsing field-level F1 (test split) | ≥ 0.85 overall; ≥ 0.95 name/email/phone |
| M2 | Normalization precision / recall | ≥ 0.90 / ≥ 0.85 |
| M3 | Matching NDCG@10 / Spearman ρ | ≥ 0.80 / ≥ 0.60 |
| M4 | API completeness | 100% of endpoints in §3.1 C5 covered by tests |
| M5 | Reliability | 0 5xx at ~10 concurrent users (`LLM_MODE=stub`) |
| M6 | Latency, single `/parse` (real Gemini) | p95 < 10 s, p50 < 5 s; cached < 200 ms |
| M7 | Hallucination rate (unverifiable fields) | ≤ 5% *(proposed)* |
| M8 | Fairness: \|Δscore\| across counterfactuals | ≤ 0.02 mean, ≤ 0.05 max *(proposed)* |
| M9 | Fine-tuned embeddings | ≥ +2 pts normalization recall; NDCG not lower *(proposed)* |
| M10 | NL search precision@10 on 30-query gold set | ≥ 0.70 *(proposed)* |

M5's target is lowered from v1 (99% at 50 users), and M7–M10 are new. Both changes are recorded in ADR-0003.

---

## 4. Step-by-Step Implementation Roadmap

Milestones run in order. Each one is done when its exit criteria have been run and recorded in `docs/progress/`.

| # | Milestone | Scope | Exit criteria |
|---|---|---|---|
| **0** | Foundation & data ✅ | Done (Phases 0–1). CI green pending a pushed branch (0-H). | Recorded in `phase-00.md`, `phase-01.md` |
| **1** | Scope cleanup | Remove Celery/Flower/Jaeger/Prometheus/OTel, webhooks, idempotency, API-key scopes, cross-process LLM limiter; Alembic migration 0002; rewrite `plan.md`/`ordered.md`; ADR-0003; update `CLAUDE.md`, `.env.example`, compose, CI | ruff, mypy, pytest green; `docker compose up` healthy with 4 services; migrations up/down clean |
| **2** | Parsing Agent + **F2** grounding | C1, evidence verifier, rule fallback, Redis parse cache | M1 on val split; M7 measured; degradation test passes with LLM disabled |
| **3** | Normalization Agent + **F5** fine-tuning | C2 cascade, hierarchy, proficiency; train and publish fine-tuned model; Chroma `skills` re-indexed | M2 on gold set; M9 before/after table |
| **4** | Matching Agent + pipeline + **F4** | C3, JD parser, LangGraph graph (C4), blind redaction, fairness harness | M3 on val (tuned), M8; partial-result tests per failing agent |
| **5** | REST API + batch + **F5** CI gate | C5 endpoints, auth, slowapi, RFC 7807, BackgroundTasks batch, `agent_runs`, eval-gate workflow | M4; M5 stub test; M6 sequential real-Gemini run; CI gate blocks a deliberately regressed PR |
| **6** | Advanced agents: **F1** + **F3** | Candidates Chroma collection, search agent + 30-query gold, coach agent with critic | M10; coach critic rejects all invented claims on a 20-case adversarial set |
| **7** | Next.js app + live demo | P1, P3, P4, P7, evidence highlighting, blind toggle; deploy backend + Vercel frontend | All pages work against the hosted API; demo usable without spending quota |
| **8** | Polish & release v1.0 | P5 eval page from final test-split reports, P6 README + GIF + diagram, `CHANGELOG`, `scripts/demo.sh` | Final test-split report published; clean-machine `docker compose up` + demo script succeed; owner tags `v1.0.0` |

The frontend (milestone 7) can start in parallel once milestone 5's OpenAPI schema is stable. Use it to generate typed API clients for Next.js (`openapi-typescript`).

---

## 5. Action Items & Next Steps

**Owner**
- [x] Review and approve this plan (approved 2026-10-13).
- [ ] Push a branch so CI runs and Phase 0 exit criterion 0-H can close.
- [ ] Pick the demo hosting target (backend VM/container host; Vercel for frontend) and a Hugging Face account for the fine-tuned model.

**Milestone 1: build first** (done 2026-10-13; see `docs/progress/milestone-01.md`)
- [x] Write ADR-0003 "Portfolio re-scope", and add plan §14 rows superseding D2/D8 (Celery), D10 (load target) and the out-of-scope UI entry.
- [x] Rewrite `documents/plan.md` and `documents/ordered.md` from this document; reset the status tracker to milestones 0–8.
- [x] Delete `src/talentgraph/worker/` (Celery app and tasks), `api/webhooks.py`, `api/idempotency.py`, `observability/tracing.py`, `observability/metrics.py`, `llm/ratelimit.py`.
- [x] Re-point the `api/ratelimit.py` and `api/auth.py` stubs at slowapi and a single env key (`API_KEY` added to settings); the implementation is Steps 5.2–5.3.
- [x] Remove `worker`, `flower`, `jaeger`, `prometheus` from `docker-compose.yml`; drop Celery, Flower, OTel, prometheus-client, pdfplumber, (Locust kept for the small M5 test) from `pyproject.toml`; `uv sync`.
- [x] Alembic `0002`: drop `webhook_deliveries`; drop `api_keys` and every `api_key_id` (one key from the environment); keep `batch_jobs`, `batch_items`, `emerging_skills` (as the unrecognized-skill store).
- [x] Remove the dropped variables from `config.py` and `.env.example`; update `CLAUDE.md`, `README.md`, CI workflow.
- [x] Run the global checks and record them in `docs/progress/` (ruff, mypy, pytest, compose up with 4 healthy services, migration round-trip and `alembic check`).

**Milestone 2: next**
- [ ] Add `verified`/`evidence` to the `ParsedResume` schema; write the Gemini extraction prompt; record FakeLLM fixtures.
- [ ] Implement PyMuPDF block ordering, section lexicon, regex extractors, evidence verifier; run `eval/parsing.py` on val.

---

## 6. Known Constraints & Risks

| Risk / constraint | Impact | Mitigation |
|---|---|---|
| **Gemini free-tier quota** (RPM/RPD) | Demo, eval runs and new agents (F1, F3) burn quota | Redis caches for parse/JD/planner/coach; demo mode with pre-cached samples; FakeLLM in CI; `stub` mode for load tests; retry once then degrade to rules |
| **Free-tier data use**: Google may use prompts | Public demo visitors could upload real resumes | Visible warning on upload; sample resumes first; optionally restrict the public demo to samples, or cap and auto-delete uploads; paid key required before real PII |
| **Gemini model churn** | Model IDs disappear | Model IDs are config values; check them at the start of each milestone |
| **Hosting a CPU embedding model** | Free hosts lack the RAM (~1.5–2 GB) for torch + model | Small paid VM or container host; model baked into the image; frontend on Vercel |
| **Windows Application Control blocks torch `_C` and mypy 2 DLLs** | Encoder, seeding and fine-tuning can't run natively | Run them in the api container or Colab; mypy pinned < 2; unit tests never load torch |
| **Synthetic data is too clean** | Inflated M1–M3 | Template variety and noise injection (already in Phase 1); plus the ADR-0004 supplements: LLM-reworded resumes, a consented real-resume check set, the TechWolf ESCO skill benchmark (CC BY 4.0) and real job postings, all reported next to the main metrics; state the limitation on the eval page |
| **Match gold from a rubric labeler, not experts** (ADR-0002) | Weak M3 claim | Re-validate with an LLM judge or a small self-labeled set before milestone 4 sign-off; report it openly |
| **LLM hallucination in extraction or coaching** | Wrong profiles, invented experience | F2 verifier and the F3 critic; M7 measured and published |
| **Bias in scoring** | Unfair rankings, a real legal topic in hiring | F4 blind mode and counterfactual audit (M8); no protected attributes used as features |
| **Fine-tuning overfits the alias pairs** | Recall gain on train only | Train/val/test split by skill, not by pair; report on the held-out test split only |
| **BackgroundTasks lose work on restart** (no Celery) | Batch items stuck | Items stay `pending`/`running` in Postgres; on startup, mark stale items `failed` and allow resubmission; batch size capped at ~20 |
| **Scope creep** from five new features | Project never ships | Strict milestone order; F1/F3 come after the core is measured; at most one stretch goal |
| **Ambiguous skills** ("Go", "R", "Swift", "Spring") | Normalization errors | `ambiguous` alias flag always routes to context-aware LLM disambiguation |
| **Owner-only git** | Agents must not commit | All git operations are done by the owner (CLAUDE.md rule) |
