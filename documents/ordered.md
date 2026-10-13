# TalentGraph: Ordered Execution Guide (v2)

> **Status note (2026-10-13):** The project was re-scoped as an AI-engineering portfolio piece (ADR-0003, plan §14 D13–D18). The 12 v1 phases became **9 milestones (0–8)**. The v1 phases 0 and 1 are done and form Milestone 0. The v1 guide is kept unchanged in [`archive/ordered-v1.md`](archive/ordered-v1.md); the "Phase 1.x" step references in `scripts/` and in `docs/progress/phase-0*.md` point there.
>
> **What this is.** The step-by-step build order. Each milestone lists its goal, steps, deliverables and **exit criteria**: objective checks that must all pass before the milestone counts as complete. Steps are numbered `M.N` (e.g. Step 2.10), and stub modules name the step that implements them.
>
> **Read first:** [`idea.md`](idea.md) (the brief), [`plan.md`](plan.md) (the design; "plan §6.2" points there) and [`project-plan-v2.md`](project-plan-v2.md) (the one-page summary).

---

## How to use this document (for humans and agents)

1. **Work strictly in order.** Don't start milestone *N+1* until every exit criterion of milestone *N* is ✅. Inside a milestone, steps can run in parallel unless one is marked **(after X.Y)**. Exception: Milestone 7 (web app) may start once Milestone 5's OpenAPI schema is stable.
2. **When you finish a milestone**, run its whole exit-criteria checklist and create `docs/progress/milestone-NN.md` from the [template](#progress-record-template). Paste the commands you ran and their real output or metric values. Never write ✅ for a check you didn't run.
3. **If a criterion can't be met**, don't lower the bar quietly. Write down what you tried, open an ADR in `docs/decisions/`, add a row to plan §14, and then adjust the target. (M7–M10 may each be adjusted once after their first measurement, by ADR.)
4. **Update the [Status Tracker](#status-tracker)** whenever a milestone starts or finishes, and [`status.md`](status.md) whenever a step or exit criterion changes state.
5. **Global rules** apply to every milestone:
   - `uv run ruff check . && uv run ruff format --check .` passes.
   - `uv run mypy` passes (strict).
   - `uv run pytest` passes offline in under 60 s (FakeLLM, no network).
   - No secrets in git. New env vars go in `config.py` and `.env.example`.
   - `CLAUDE.md` is updated when commands or architecture change.
   - **Don't commit or push.** The owner does all git operations.
   - **Free-tier hygiene:** never send real resumes to the Gemini free tier; record roughly how much LLM quota a milestone used.

### Status tracker

Step-by-step done/pending detail, owner actions and the metrics scoreboard are in [`status.md`](status.md).

| Milestone | Name | Status | Progress record |
|---|---|---|---|
| 0 | Foundation & data (v1 Phases 0–1) | 🟨 Done except 0-H (CI green), which needs the owner to push a branch | [phase-00](../docs/progress/phase-00.md), [phase-01](../docs/progress/phase-01.md) |
| 1 | Scope cleanup | ✅ Done 2026-10-13 (all of 1-A to 1-E pass) | [milestone-01](../docs/progress/milestone-01.md) |
| 2 | Parsing Agent + grounded extraction (F2) | ⬜ Not started | n/a |
| 3 | Normalization Agent + fine-tuned embeddings (F5) | ⬜ Not started | n/a |
| 4 | Matching Agent + pipeline + blind screening (F4) | ⬜ Not started | n/a |
| 5 | REST API, batches, CI eval gate (F5) | ⬜ Not started | n/a |
| 6 | Talent Search (F1) + Career Coach (F3) | ⬜ Not started | n/a |
| 7 | Next.js web app + live demo | ⬜ Not started | n/a |
| 8 | Polish & v1.0 release | ⬜ Not started | n/a |

Legend: ⬜ Not started · 🟨 In progress · ✅ Complete · ⛔ Blocked (give the reason in the progress record)

### Dependency graph

```
0 ─▶ 1 ─▶ 2 ─▶ 3 ─▶ 4 ─▶ 5 ─▶ 6 ─▶ 8
                          └──────▶ 7 ─┘   (7 can start once 5's OpenAPI is stable)
```

---

## Milestone 0: Foundation & data ✅ (v1 Phases 0–1)

Done. Scaffolding, tooling, Docker Compose, CI config, the Gemini/FakeLLM wrapper, the DB schema, the taxonomy (9,642 skills, 15,122 aliases), 560 synthetic resumes, 120 JDs and the gold sets. Details and evidence: [`phase-00.md`](../docs/progress/phase-00.md), [`phase-01.md`](../docs/progress/phase-01.md), [`data/README.md`](../data/README.md).

**Open item:** 0-H (CI green) needs the owner to push a branch.

---

## Milestone 1: Scope cleanup

**Goal:** the repository matches the v2 scope. Removed features are gone from code, config, compose and docs; nothing half-removed is left behind.
**Depends on:** Milestone 0.

### Steps

**1.1 Decision records.** Write ADR-0003; add plan §14 rows D13–D18 (old rows untouched).

**1.2 Planning docs.** Archive v1 `plan.md` / `ordered.md` to `documents/archive/`; write the v2 versions and `project-plan-v2.md`.

**1.3 Remove code.** Delete:
- `worker/` (Celery), `api/webhooks.py`, `api/idempotency.py`
- `llm/ratelimit.py`, `observability/tracing.py`, `observability/metrics.py`
- `deploy/`, `scripts/create_api_key.py`, `scripts/train_section_clf.py`, `eval/api_contract.py`

Then simplify `llm/client.py`: no shared limiter, no fallback model, and a 429 after retries raises `LLMQuotaExceeded`. Remove the `/metrics` mount from `api/main.py`.

**1.4 Schema.** Alembic `0002_portfolio_rescope`:
- drop `webhook_deliveries`, `batch_jobs.callback_url`, `api_keys` and every `api_key_id`
- drop the review columns of `emerging_skills`

Update `db/models.py` and `tests/unit/test_models_schema.py` to match.

**1.5 Config and dependencies.**
- `config.py` / `.env.example`:
  - drop the Celery, fallback-model, RPM/RPD, webhook, OTel and in-flight settings
  - add `API_KEY` and `RATE_LIMIT_PER_MIN`
  - set `MAX_BATCH_FILES=20`
- `pyproject.toml`:
  - drop celery, flower, pdfplumber, prometheus-client and opentelemetry-*
  - move scikit-learn to dev
  - then run `uv lock && uv sync`
- `docker-compose.yml`: keep only `api`, `postgres`, `redis` and `chroma`.

**1.6 Re-point stubs.**
- Every stub docstring names its v2 step.
- Add stubs for the new modules: `parsing/verify.py`, `matching/blind.py`, `agents/search/`, `agents/coach/`, `routers/search.py`, `routers/coach.py`, `scripts/finetune_embeddings.py`, `eval/fairness.py`, `eval/search.py`, `eval/coach.py`.
- Trim `config/matching.yaml` (no semantic weight) and `config/proficiency.yaml` (years + wording only).

**1.7 Docs.** Update `CLAUDE.md` and `README.md` for the new stack and commands.

### Exit criteria

| # | Check | How to verify | Pass condition |
|---|---|---|---|
| 1-A | Lint, types, tests | `uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest` | All exit 0 |
| 1-B | Nothing removed is still referenced | `grep -rniE "celery\|webhook\|idempotency\|opentelemetry\|prometheus\|pdfplumber\|flower\|jaeger\|fallback_model\|rpm_limit" src tests eval config pyproject.toml docker-compose.yml .env.example .github Dockerfile` (`scripts/` is excluded: the taxonomy generators name Prometheus, Jaeger and OpenTelemetry as *skills*) | No matches |
| 1-C | Stack comes up | `docker compose up -d --build --wait`, then `docker compose ps` | 4 services, all `healthy` |
| 1-D | Migrations round-trip | `docker compose exec api alembic upgrade head`, `alembic downgrade 0001_initial_schema`, `alembic upgrade head` | No errors; tables match plan §7.1 |
| 1-E | Docs consistent | Read `CLAUDE.md`, `README.md`, plan §14, ADR-0003 | No v1-only commands or services remain; D13–D18 present; D1–D12 unchanged |

---

## Milestone 2: Parsing Agent + grounded extraction (F2)

**Goal:** a `ParsingAgent` that turns PDF, DOCX or TXT into a validated `ParsedResume`, with every LLM field carrying verified evidence. It must meet M1 on val and measure M7. Design: plan §6.1.
**Depends on:** Milestone 1.

### Steps

**2.1 Schema.** Write the full `ParsedResume` and `ResumeExtraction` in `core/schemas/resume.py`, with `{value, confidence, evidence, verified}` on every LLM field and `meta.unverified_count`. Bump `schema_version`. Check that every Phase 1 `.gt.json` still validates; adjust the generators only if needed (then `regenerate_data.py --check`).

**2.2 Type detection** (`detect.py`): magic bytes, size limit and page limit. Errors are `UnsupportedFileType` and `FileTooLarge`.

**2.3 Layout model** (`layout.py`): `Block` and `LayoutDocument`.

**2.4 PDF** (`pdf.py`): PyMuPDF blocks, x-position column ordering, `find_tables()`, scanned-page check (`UnsupportedContent`).

**2.5 DOCX** (`docx.py`): paragraphs and tables in order, text boxes through XML, heading styles.

**2.6 TXT** (`text.py`): encoding detection, paragraphs, header hints.

**2.7 Sections** (`sections.py`): expand `config/section_lexicon.yaml` to 150+ variants; add typography and position signals.

**2.8 Rules** (`rules.py`): email, phone, URLs, date ranges, alias-index skill candidates.

**2.9 LLM extraction** (`llm_extract.py`): prompt in `llm/prompts/parse_resume.md`. Record FakeLLM fixtures for the fixture resumes with `scripts/record_llm_fixtures.py` (real key, synthetic data only).

**2.10 Evidence verifier** (`verify.py`, F2): rapidfuzz alignment of each evidence span against the source text. At ≥ 90 the field is verified; otherwise its confidence is halved and the miss is counted.

**2.11 ParsingAgent** (`agent.py`): merge rules and LLM output, validate, compute the quality score, and fall back to rules-only output when the LLM fails.

**2.12 Parse cache:** a Redis cache keyed by `sha256(file)` + `PIPELINE_VERSION`.

**2.13 Evaluation:**
- `eval/parsing.py`: per-field P/R/F1, list entities aligned in order, hallucination rate.
- Run it on val and iterate.
- Run `eval/latency.py` for the parser alone.

**2.14 Reworded resumes (ADR-0004 A):**
- `scripts/reword_resumes.py` has Gemini rewrite the summaries and experience bullets of about 100 val/test profiles. It is resumable and checkpointed, and it validates that names, dates, companies and skills are unchanged.
- Render the rewritten profiles with the existing templates into `data/resumes/{val,test}_reworded/`.
- Report M1 on them.

**2.15 Real-resume check set (ADR-0004 B):**
- Collect 10–20 consented resumes into `data/private/real_resumes/` (gitignored), with hand-labeled `.gt.json` files.
- The consent must cover processing by the Gemini free tier.
- Report M1 on them. Use them for reporting only, never for tuning.

### Exit criteria

| # | Check | Pass condition |
|---|---|---|
| 2-A | Unit tests | Each extractor, the verifier and the merge rules are tested on `tests/fixtures/resumes/` (all 6 templates, 3 formats) |
| 2-B | M1 on val | F1 ≥ 0.85 overall; ≥ 0.95 for name, email and phone |
| 2-C | M7 on val | Hallucination rate measured and ≤ 5%. A deliberately corrupted fixture (fake evidence) is flagged `verified: false` |
| 2-D | Degradation | With `LLM_MODE=fake` and no fixture (or a forced `LLMQuotaExceeded`), status is `partial` and contact fields are still extracted |
| 2-E | Error cases | PNG → 415; 11 MB file → 413; scanned PDF → 422 `unsupported_content` |
| 2-F | Latency | Parser p95 < 7 s on 20 val resumes with the real API (sequential, within quota); cache hit < 200 ms |
| 2-G | Supplementary M1 | M1 reported on the reworded val set and on the real check set (no target). Nothing from `data/private/` appears in git or `reports/` |

---

## Milestone 3: Normalization Agent + fine-tuned embeddings (F5)

**Goal:** a `NormalizationAgent` that maps raw skills to canonical IDs, infers hierarchy, estimates proficiency and lists unrecognized skills. It must meet M2; then fine-tune the embedding model and measure M9. Design: plan §6.2.
**Depends on:** Milestone 2.

### Steps

**3.1 Schemas and repository.** `SkillProfile` in `core/schemas/skills.py`. `db/repositories/taxonomy.py`: alias index, ancestors, children, implications, relations, cached per `taxonomy_version`.

**3.2 Cleaning** (`clean.py`): case, versions, punctuation, splitting lists.

**3.3 Skill index:** confirm that the Chroma `skills` collection (seeded in Phase 1) matches the alias index; add a query helper.

**3.4 Cascade** (`cascade.py`): exact → fuzzy → embedding → batched LLM → unrecognized, with thresholds from `config/normalization.yaml`. Ambiguous aliases always go to the LLM step when context exists.

**3.5 Hierarchy** (`hierarchy.py`): implication rules and ancestors, `inferred: true`.

**3.6 Proficiency** (`proficiency.py`): years used (overlaps merged) plus qualifier wording; skills-section-only entries capped at 2.

**3.7 Unrecognized store** (`emerging.py`): upsert into `emerging_skills` with occurrence count and up to 5 example contexts.

**3.8 NormalizationAgent** (`agent.py`): `ParsedResume` → `SkillProfile`; quality score.

**3.9 Evaluation and tuning:** `eval/normalization.py` on the gold set (precision, recall, unrecognized rate, worst errors). Tune the thresholds and the proficiency config on train/val.

**3.10 Fine-tuning (F5)** (`scripts/finetune_embeddings.py`; run in Docker or Colab):
1. Build (alias, canonical) pairs from the train skills; split by skill.
2. Train with `MultipleNegativesRankingLoss`.
3. Push to the Hugging Face Hub and pin the revision in `EMBEDDING_MODEL`.
4. Re-seed Chroma `skills` and bump `PIPELINE_VERSION`.
5. Re-run 3.9 with the base and the fine-tuned model.

**3.11 External benchmarks (ADR-0004 D, E2):**
- `scripts/fetch_external.py` downloads the pinned revisions of TechWolf `skill-extraction-{techwolf,tech,house}` and `lukebarousse/data_jobs` into the gitignored `data/external/raw/`, and writes `data/external/ATTRIBUTION.md`.
- Build the ESCO → slug crosswalk by exact name/alias match only, never through the cascade. Spot-check 100 mappings by hand.
- `eval/external.py` reports, for the base and the fine-tuned model:
  - normalization precision/recall on the crosswalked spans, with coverage
  - the unrecognized rate on `data_jobs` skill strings

### Exit criteria

| # | Check | Pass condition |
|---|---|---|
| 3-A | Required examples | `JS`, `K8s`, `React.js`, `ReactJS`, `ML Engineering` and the other 1-D examples map correctly through the agent |
| 3-B | M2 on test | Precision ≥ 0.90, recall ≥ 0.85 |
| 3-C | Hierarchy | TensorFlow + PyTorch ⇒ Deep Learning (inferred); inferred skills never outrank explicit ones |
| 3-D | Proficiency | Unit tests cover the year bands, wording ±1 and the skills-only cap |
| 3-E | M9 | Fine-tuned model ≥ +2 pts recall over the base on the test split; before/after table saved to `reports/` |
| 3-F | Degradation | With no LLM, ambiguous skills fall back to the best embedding candidate or unrecognized, and status is `partial` |
| 3-G | External check | TechWolf crosswalk coverage, and P/R for the base and fine-tuned models, saved to `reports/`; the `data_jobs` unrecognized rate reported (no targets) |

---

## Milestone 4: Matching Agent + pipeline + blind screening (F4)

**Goal:** an explainable `MatchingAgent` tuned to meet M3, the LangGraph pipeline with graceful degradation, and blind mode with a fairness audit (M8). Design: plan §4.2, §6.3.
**Depends on:** Milestone 3.

### Steps

**4.1 Job parsing:** `JobRequirements` and `MatchResult` schemas; `job_parser.py` (one cached LLM call, then normalization).

**4.2 Scoring** (`scoring.py`): per-requirement credit, `S_skill`, `S_exp`, penalty. Pure functions, unit-tested.

**4.3 Thresholds** (`thresholds.py`): presets and validation.

**4.4 Gaps** (`gaps.py`): missing skills, current vs. required level, upskilling hints from `related` and sibling edges.

**4.5 MatchingAgent** (`agent.py`): score, breakdown, gaps, and a `rank()` helper.

**4.6 Agent protocol and state:**
- Simplify `core/schemas/messages.py` to `AgentResult` / `AgentError` (plan §5).
- Write `PipelineState`.
- Write `run_agent()` in `agents/base.py`: timeout, retries on `retryable` errors, an `AgentRun` per attempt, persisted to `agent_runs`.

**4.7 Graph** (`graph.py`): `run_parse_pipeline` and `run_match_pipeline` with the degradation edges from plan §4.2.

**4.8 Blind mode** (`matching/blind.py`): the redaction step and graph branch. Add an Alembic migration for `matches.blind`.

**4.9 Evaluation and tuning:**
1. **Re-validate the match gold first** (ADR-0002): either run the LLM judge on a sample, or collect human labels for `human_labeling.csv` and report κ.
2. Tune α, β, λ and the presets on train/val with `scripts/tune_matching.py`.
3. Run `eval/matching.py` on test.

**4.10 Fairness audit** (`eval/fairness.py`, M8): counterfactual variants of the test resumes (names across gender and ethnicity, pronouns, graduation years), scored in normal and blind mode.

**4.11 Real job postings (ADR-0004 E1):**
- `scripts/fetch_usajobs.py` (owner's `USAJOBS_API_KEY`) pulls about 100 IT and data postings into the gitignored `data/external/raw/usajobs/`. Postings are stored unmodified and credited to USAJOBS.
- Run the JD parser on them and spot-check 30 by hand: share of requirements extracted correctly, and failures.
- Keep the postings for evaluation only, until the owner confirms public reuse with OPM (ADR-0004).

### Exit criteria

| # | Check | Pass condition |
|---|---|---|
| 4-A | M3 on test | NDCG@10 ≥ 0.80 and Spearman ρ ≥ 0.60, and the report states which gold re-validation was used |
| 4-B | Explainability | Every `MatchResult` has a per-requirement breakdown that sums to the reported skill score (unit test) |
| 4-C | Degradation | With the normalizer and the matcher each forced to fail in turn, the pipeline returns `partial` with the earlier outputs intact (unit tests through the graph) |
| 4-D | Blind mode | A redaction unit test covers each signal class; blind and normal scores both reported |
| 4-E | M8 | Mean \|Δscore\| ≤ 0.02 and max ≤ 0.05 across counterfactuals (blind mode at least); results saved to `reports/` |
| 4-F | Real JDs | The JD parser runs on the USAJOBS set without errors; the 30-posting spot-check result is recorded in the progress record |

---

## Milestone 5: REST API, batches, CI eval gate (F5)

**Goal:** every §8 endpoint except search and coach, with one API key, slowapi limits, RFC 7807 errors and background batches. Also: measure M4–M6 and turn on the CI eval gate. Design: plan §8.
**Depends on:** Milestone 4.

### Steps

**5.1 Dependencies** (`deps.py`): settings, DB session, agents from the app lifespan. Add CORS with a `WEB_ORIGIN` setting.

**5.2 Auth** (`auth.py`): an `X-API-Key` check against `API_KEY` on write endpoints; 401 when missing or wrong.

**5.3 Rate limiting** (`ratelimit.py`): add slowapi with per-IP `RATE_LIMIT_PER_MIN` and a lower limit on LLM-heavy routes; 429 with `Retry-After`.

**5.4 Sync routers:** `parse`, `candidates`, `match` (plus `/rank`, `?blind=true`) and `skills`. Use the response envelope with `?include=trace`.

**5.5 Batches:**
- `orchestrator/batch.py`, `routers/batch.py`, `routers/jobs.py`.
- Run batches with BackgroundTasks and bounded concurrency.
- On startup, mark stale `running` items `failed`.

**5.6 Logging hygiene:** a PII-scrubbing structlog processor; `agent_runs` holds no payloads; uploads are deleted after processing unless `RETAIN_UPLOADS`.

**5.7 API tests:** `tests/e2e/` covers every endpoint, with valid and invalid inputs, and validates `/openapi.json` with `openapi-spec-validator`. Add `examples/` (a cURL walkthrough and one Python script).

**5.8 Performance:** `eval/latency.py` (real API, sequential) and `eval/load/locustfile.py` (~10 users, `LLM_MODE=stub`).

**5.9 CI eval gate (F5):**
- Commit `reports/baseline/`.
- Add a CI job that runs the parsing, normalization and matching evals on a fixed val subset with FakeLLM fixtures.
- The job fails when a metric drops more than its tolerance.

### Exit criteria

| # | Check | Pass condition |
|---|---|---|
| 5-A | M4 | Every §8 endpoint in scope has passing e2e tests; the OpenAPI schema validates with 0 errors |
| 5-B | Errors | Each `TalentGraphError` subclass renders as problem+json with the right status (tests) |
| 5-C | Auth and limits | No key → 401 on write endpoints; exceeding the limit → 429 with `Retry-After` |
| 5-D | Batches | A 20-file batch completes with per-item statuses. A simulated restart marks stale items `failed` |
| 5-E | M5 | 0 5xx at ~10 concurrent users for 5 minutes (`LLM_MODE=stub`) |
| 5-F | M6 | `/parse` p95 < 10 s and p50 < 5 s over 30 sequential test-split resumes (real API); cache hit < 200 ms |
| 5-G | CI gate | A deliberately regressed branch fails the eval job; reverting it passes (owner pushes) |

---

## Milestone 6: Talent Search (F1) + Career Coach (F3)

**Goal:** the two advanced agents, measured against their own gold sets. Design: plan §6.4, §6.5.
**Depends on:** Milestone 5.

### Steps

**6.1 Candidate index:** a Chroma `candidates` collection (summary + canonical skills + titles), written on persist and back-filled by a script.

**6.2 Search agent** (`agents/search/`): `SearchPlan` planner (cached), the four tools, a LangGraph `ToolNode` loop (≤ 4 rounds), re-ranking with evidence citations, and the no-LLM fallback.

**6.3 Search evaluation:** build a 30-query gold set from profile ground truth (`data/eval/search_gold.json`); `eval/search.py` scores precision@10.

**6.4 Coach agent** (`agents/coach/`): the `CoachReport` schema; generate → critic (deterministic, then LLM) → revise, at most 2 revisions; cache.

**6.5 Coach evaluation:** a 20-case adversarial set (`data/eval/coach_adversarial.json`); `eval/coach.py` counts unsupported claims after the critic.

**6.6 Routers:** `POST /search` and `POST /coach`, with tests.

### Exit criteria

| # | Check | Pass condition |
|---|---|---|
| 6-A | M10 | Precision@10 ≥ 0.70 on the search gold set |
| 6-B | Coach | 0 unsupported claims in final outputs on the adversarial set; every removed claim is listed in the report |
| 6-C | Degradation | With no LLM, `/search` returns `partial` results from the keyword planner; `/coach` returns 503 problem+json, not a 500 |
| 6-D | Quota | A repeat request for the same query or candidate+job makes 0 LLM calls (cache test) |

---

## Milestone 7: Next.js web app + live demo

**Goal:** a reviewer can use every feature from a public URL without spending Gemini quota. Design: plan §9.
**Depends on:** Milestone 5 (pages for search and coach also need Milestone 6).

### Steps

**7.1 Scaffold** `web/`: Next.js (App Router, TypeScript), Tailwind, typed client from `openapi-typescript`, and a server-side route handler that adds the API key.

**7.2 Pages:** Upload & Profile, Match ("why this score"), Recruiter Ranking, Talent Search, Coach, Taxonomy, About. Responsive, light and dark.

**7.3 Evidence highlighting:** render PDFs with react-pdf; highlight verified spans; badge unverified fields.

**7.4 Demo mode:** `scripts/seed_demo.py` (≈30 resumes, 10 JDs, results pre-computed and cached), `demo` flags on candidates and jobs, an upload warning, upload caps.

**7.5 Deploy:** backend (`api` + Postgres + Redis + Chroma) on a small VM or container host; frontend on Vercel; CORS and secrets configured.

### Exit criteria

| # | Check | Pass condition |
|---|---|---|
| 7-A | Pages work | Each page works against the hosted API (manual checklist with screenshots in the progress record) |
| 7-B | No quota on samples | The whole demo path on samples makes 0 Gemini calls (checked in the API logs) |
| 7-C | Key stays server-side | The API key doesn't appear in the browser bundle or in network requests from the browser |
| 7-D | Mobile | Pages are usable at 375 px width with no horizontal scroll |

---

## Milestone 8: Polish & v1.0 release

**Goal:** a reviewer understands the project in two minutes from the README, and the measured results are public.
**Depends on:** Milestones 6 and 7.

### Steps

**8.1 Final evaluation:** run every `eval/` script on the test split; commit `reports/final/`.

**8.2 Evaluation page:** M1–M10 tables and charts, the PR curve, the fairness audit and the fine-tuning before/after, all built from `reports/final/`. State the dataset limitations (synthetic data, rubric gold).

**8.3 README:** live link, demo GIF, architecture diagram, metrics table, "design decisions" with ADR links, a quick start.

**8.4 Release:** `CHANGELOG.md`, `scripts/demo.sh` (seed, parse 5, match 2 JDs, search, coach), version `1.0.0`, and a final pass on `CLAUDE.md`, `README.md` and the status tracker. The owner tags `v1.0.0`.

**8.5 Optional:** at most one runner-up feature: live agent progress over SSE, Langfuse LLM tracing, or multimodal parsing of hard PDF pages.

### Exit criteria

| # | Check | Pass condition |
|---|---|---|
| 8-A | Clean install | `git clone`, `docker compose up -d`, `scripts/demo.sh` succeeds on a machine with only Docker |
| 8-B | Results public | The evaluation page shows M1–M10 from `reports/final/` with the git SHA |
| 8-C | Docs current | README, `CLAUDE.md` and the status tracker (all ✅) are up to date; `CHANGELOG.md` covers every milestone |

---

## Progress record template

Copy this to `docs/progress/milestone-NN.md` when a milestone is complete:

```markdown
# Milestone NN: <name>: progress record

- **Completed by:** <agent/person>   **Date:** YYYY-MM-DD   **Git SHA:** <sha, or "uncommitted">
- **LLM quota used:** <approx. requests; model>
- **Status:** ✅ Complete | 🟨 In progress | ⛔ Blocked

## Exit criteria results
| # | Check | Command run | Result / metric | Pass? |
|---|---|---|---|---|
| N-A | ... | `...` | ... | ✅/❌ |

## Iteration log (metrics milestones only)
| Iteration | Change | Metric before → after |
|---|---|---|

## Deviations from plan
- <what changed, why, link to ADR>

## Known issues / follow-ups
- ...

## Handoff notes for the next milestone
- <env vars added, data regenerated, gotchas>
```
