# TalentGraph: Project Status

> **Last updated:** 2026-10-17 · **Current milestone:** 2 (Parsing Agent + F2), 🟨 in progress · Milestones 0 and 1 ✅
>
> This page lists every milestone and step and whether it's done. The steps and their exit criteria are defined in [`ordered.md`](ordered.md), and the evidence for completed work is in [`docs/progress/`](../docs/progress/). Update this page whenever a step or exit criterion changes state.

**Legend:** ✅ done · 🟨 in progress / partly done · ⏳ waiting on the owner or an external dependency · ⬜ not started · ➖ dropped (no longer in scope)

---

## Overview

| Milestone | Name | Steps done | Exit criteria | Status |
|---|---|---|---|---|
| 0 | Foundation & data (v1 Phases 0–1) | all | 18 / 18 | ✅ |
| 1 | Scope cleanup | 7 / 7 | 5 / 5 | ✅ |
| 2 | Parsing Agent + grounded extraction (F2) | 11 / 15 | 3 / 7 | 🟨 (real-API runs wait on quota) |
| 3 | Normalization Agent + fine-tuned embeddings (F5) | 0 / 11 | 0 / 7 | ⬜ |
| 4 | Matching Agent + pipeline + blind screening (F4) | 0 / 11 | 0 / 6 | ⬜ |
| 5 | REST API, batches, CI eval gate (F5) | 0 / 9 | 0 / 7 | ⬜ |
| 6 | Talent Search (F1) + Career Coach (F3) | 0 / 6 | 0 / 4 | ⬜ |
| 7 | Next.js web app + live demo | 0 / 5 | 0 / 4 | ⬜ |
| 8 | Polish & v1.0 release | 0 / 5 | 0 / 3 | ⬜ |

## Waiting on the owner

| # | Action | Unblocks | Status |
|---|---|---|---|
| 1 | Start Docker Desktop and run the compose and migration checks | 1-C, 1-D → Milestone 1 ✅ | ✅ done 2026-10-13 |
| 2 | Review and commit the changes, then push a branch so CI runs | 0-H → Milestone 0 ✅ | ✅ done 2026-10-13 (CI run 38409286091) |
| 3 | Remove the deleted variables (`CELERY_*`, `LLM_FALLBACK_MODEL`, …) from your local `.env` and add `API_KEY=` | Clean config (not blocking) | ⏳ |
| 4 | Set `GEMINI_API_KEY` in `.env` | Step 2.9 (record LLM fixtures), 2.14 | ✅ set |
| 8 | Decide how to get Gemini quota (`gemini-3.8-flash` free tier = **20 requests/day**) | 2.9, 2.13, 2.14 | ✅ 2026-10-15: stay on the free tier and run daily |
| 9 | **Once a day** (any time; quota resets daily): `docker compose run --rm tools uv run python scripts/daily_llm_batch.py`. It continues where the last run stopped (88 val fixtures → 100 rewordings → reworded val fixtures); `--status` shows progress. About 50% of calls currently fail with 503 "high demand", so expect ~10 resumes/day, roughly 3–4 weeks in total | 2.9, 2.13, 2.14 → 2-B, 2-C, 2-F, 2-G | ⏳ daily |
| 5 | Collect 10–20 resumes with written consent, including consent to Gemini free-tier processing | Step 2.15 | ⏳ |
| 6 | Register a USAJOBS API key (and ask access@usajobs.gov whether postings may be shown in the demo) | Step 4.11 | ⏳ |
| 7 | Choose demo hosting (backend VM/container host, Vercel for the frontend) and create a Hugging Face account | Steps 3.10, 7.5 | ⏳ |

---

## Milestone 0: Foundation & data ✅

Done in v1 Phases 0–1. Evidence: [`phase-00.md`](../docs/progress/phase-00.md), [`phase-01.md`](../docs/progress/phase-01.md).

| # | Exit criterion | Status |
|---|---|---|
| 0-A | Lint and types clean | ✅ |
| 0-B | Unit tests run offline | ✅ |
| 0-C | Stack comes up (v1 7-service stack; v2 re-check is 1-C) | ✅ |
| 0-D | `/health` and `/ready` | ✅ |
| 0-E | Migrations apply cleanly (v2 re-check is 1-D) | ✅ |
| 0-F | OpenAPI served | ✅ |
| 0-G | LLM wrapper safe (FakeLLM fallback) | ✅ |
| 0-H | CI green on a pushed branch | ✅ (run 38409286091) |
| 0-I | Celery worker ping | ✅ then ➖ (Celery removed by ADR-0003) |
| 1-A | Taxonomy size: 9,642 skills, 15,122 aliases | ✅ |
| 1-B | Taxonomy integrity tests | ✅ |
| 1-C | DB and vector parity | ✅ |
| 1-D | Required examples resolve (`js`, `k8s`, `react.js`, …) | ✅ |
| 1-E | Resume corpus: 560 resumes, 6 templates, 11 industries | ✅ |
| 1-F | Job corpus: 120 JDs | ✅ |
| 1-G | Gold sets: 1,200 normalization pairs, 2,400 match pairs | ✅ |
| 1-H | Label quality (human κ pending, allowed) | ✅ |
| 1-I | Byte-for-byte reproducibility | ✅ |

## Milestone 1: Scope cleanup ✅

Evidence: [`milestone-01.md`](../docs/progress/milestone-01.md).

| Step | Task | Status |
|---|---|---|
| 1.1 | ADR-0003 and decision-log rows D13–D18 | ✅ |
| 1.2 | Archive v1 docs; write the v2 `plan.md`, `ordered.md`, `project-plan-v2.md` | ✅ |
| 1.3 | Delete Celery, webhooks, idempotency, quota limiter, tracing and metrics code; simplify the LLM client | ✅ |
| 1.4 | Migration `0002_portfolio_rescope`; ORM models and tests updated | ✅ |
| 1.5 | Settings, `.env.example`, dependencies (`uv lock`/`sync`), compose down to 4 services | ✅ |
| 1.6 | Stub docstrings point at v2 steps; new feature stubs; config files trimmed | ✅ |
| 1.7 | `CLAUDE.md` and `README.md` updated | ✅ |
| extra | ADR-0004 (real-world and external data) added to plan and build order | ✅ |

| # | Exit criterion | Status |
|---|---|---|
| 1-A | Lint, types, tests (53 passed) | ✅ |
| 1-B | No references to removed features | ✅ |
| 1-C | Compose stack (4 services) healthy | ✅ |
| 1-D | Migrations round-trip (`0001` ↔ `0002`); `alembic check` clean after the `emerging_skills` index fix | ✅ |
| 1-E | Docs consistent; D1–D12 unchanged | ✅ |

## Milestone 2: Parsing Agent + grounded extraction (F2) 🟨

Evidence so far: [`milestone-02.md`](../docs/progress/milestone-02.md).

| Step | Task | Status |
|---|---|---|
| 2.1 | Full `ParsedResume` / `ResumeExtraction` schema with evidence and `verified` | ✅ (schema 2.0; all 560 `.gt.json` validate unchanged) |
| 2.2 | File type detection and limits | ✅ |
| 2.3 | `Block` / `LayoutDocument` model | ✅ |
| 2.4 | PDF extraction (PyMuPDF, column ordering, tables, scanned check) | ✅ (recursive XY-cut; tables row by row) |
| 2.5 | DOCX extraction | ✅ |
| 2.6 | TXT extraction | ✅ |
| 2.7 | Section detection (150+ header variants) | ✅ (180 variants; sections match on 472/472 train+val) |
| 2.8 | Rule extractors (email, phone, URLs, dates, skills) | ✅ (contact, links, dates 88/88 on val) |
| 2.9 | Gemini extraction plus recorded FakeLLM fixtures | 🟨 prompt frozen 2026-10-15 (compact output, ADR-0005 amendment); fixtures **19/88** (2026-10-17: 19/19 calls succeeded), recorded daily (owner action 9) |
| 2.10 | Evidence verifier (F2) | ✅ |
| 2.11 | ParsingAgent: merge, validate, quality, degradation | ✅ |
| 2.12 | Redis parse cache | ✅ (hit latency measured in 2-F) |
| 2.13 | Evaluation: F1, hallucination rate, latency | 🟨 harness done; rules-only val F1 0.463; first 8 val resumes with Gemini (pre-compact prompt): F1 1.000, 0/222 unverified; frozen prompt, first 19 val: **F1 0.999, 0/497 unverified**; full val run ⏳ daily recording |
| 2.14 | LLM-reworded resumes (ADR-0004 A) | 🟨 script done (budgeted, resumable); runs after the val fixtures (owner action 9) |
| 2.15 | Consented real-resume check set (ADR-0004 B) | ⬜ (needs consented resumes) |

| # | Exit criterion | Status |
|---|---|---|
| 2-A | Unit tests for every extractor, the verifier and merge rules | ✅ |
| 2-B | M1 on val: F1 ≥ 0.85; ≥ 0.95 name/email/phone | 🟨 19/88 val: F1 0.999, contact 1.000; full val ⏳ |
| 2-C | M7: hallucination rate ≤ 5% | 🟨 corrupted extraction flagged ✅; 19/88 val: 0.0%; full val ⏳ |
| 2-D | Degradation to rules-only `partial` | ✅ |
| 2-E | Error cases (415, 413, 422) | ✅ |
| 2-F | Parser p95 < 7 s; cache hit < 200 ms | 🟨 frozen prompt, 19 real calls: p50 4.3 s, **p95 8.0 s** (misses 7 s); old prompt p95 19.3 s; sample of 20 builds up from the daily runs (`eval.latency --from-records`) |
| 2-G | M1 reported on the reworded and real sets; no private data in git | ⏳ reworded: daily runs; real set: owner action 5 (owner: not yet, keep pending) |

## Milestone 3: Normalization Agent + fine-tuned embeddings (F5) ⬜

| Step | Task | Status |
|---|---|---|
| 3.1 | `SkillProfile` schema; taxonomy repository | ⬜ |
| 3.2 | Raw skill cleaning | ⬜ |
| 3.3 | Chroma skill index check and query helper | ⬜ |
| 3.4 | Normalization cascade | ⬜ |
| 3.5 | Hierarchy inference | ⬜ |
| 3.6 | Proficiency (years + wording) | ⬜ |
| 3.7 | Unrecognized-skill store | ⬜ |
| 3.8 | NormalizationAgent | ⬜ |
| 3.9 | Evaluation and tuning | ⬜ |
| 3.10 | Fine-tune embeddings, publish to Hugging Face, re-index | ⬜ |
| 3.11 | External benchmarks: TechWolf ESCO crosswalk, `data_jobs` | ⬜ |

| # | Exit criterion | Status |
|---|---|---|
| 3-A | Required examples map correctly | ⬜ |
| 3-B | M2 on test: precision ≥ 0.90, recall ≥ 0.85 | ⬜ |
| 3-C | Hierarchy inference | ⬜ |
| 3-D | Proficiency unit tests | ⬜ |
| 3-E | M9: fine-tuned ≥ +2 pts recall | ⬜ |
| 3-F | Degradation without the LLM | ⬜ |
| 3-G | External check reported | ⬜ |

## Milestone 4: Matching Agent + pipeline + blind screening (F4) ⬜

| Step | Task | Status |
|---|---|---|
| 4.1 | `JobRequirements` / `MatchResult`; JD parser | ⬜ |
| 4.2 | Scoring functions | ⬜ |
| 4.3 | Threshold presets | ⬜ |
| 4.4 | Gap analysis and upskilling hints | ⬜ |
| 4.5 | MatchingAgent and `rank()` | ⬜ |
| 4.6 | Simplified agent protocol, `PipelineState`, `run_agent()` | ⬜ |
| 4.7 | LangGraph pipeline with degradation | ⬜ |
| 4.8 | Blind-mode redaction | ⬜ |
| 4.9 | Re-validate match gold; tune; evaluate | ⬜ |
| 4.10 | Fairness audit | ⬜ |
| 4.11 | Real job postings from USAJOBS | ⬜ (needs USAJOBS key) |

| # | Exit criterion | Status |
|---|---|---|
| 4-A | M3 on test: NDCG@10 ≥ 0.80, ρ ≥ 0.60 | ⬜ |
| 4-B | Explainability breakdown sums correctly | ⬜ |
| 4-C | Pipeline degradation | ⬜ |
| 4-D | Blind-mode redaction tests | ⬜ |
| 4-E | M8: fairness Δ ≤ 0.02 mean, ≤ 0.05 max | ⬜ |
| 4-F | JD parser on real postings | ⬜ |

## Milestone 5: REST API, batches, CI eval gate (F5) ⬜

| Step | Task | Status |
|---|---|---|
| 5.1 | Shared dependencies; CORS | ⬜ |
| 5.2 | Single API key auth | ⬜ |
| 5.3 | slowapi rate limiting | ⬜ |
| 5.4 | Routers: parse, candidates, match, rank, skills | ⬜ |
| 5.5 | Background batches with stale-item recovery | ⬜ |
| 5.6 | Logging hygiene (PII scrubbing) | ⬜ |
| 5.7 | e2e API tests; `examples/` | ⬜ |
| 5.8 | Latency and small load test | ⬜ |
| 5.9 | CI eval gate | ⬜ |

| # | Exit criterion | Status |
|---|---|---|
| 5-A | M4: all endpoints tested; OpenAPI valid | ⬜ |
| 5-B | RFC 7807 errors | ⬜ |
| 5-C | Auth and rate limits | ⬜ |
| 5-D | Batches and restart recovery | ⬜ |
| 5-E | M5: 0 5xx at ~10 users | ⬜ |
| 5-F | M6: p95 < 10 s, p50 < 5 s | ⬜ |
| 5-G | CI gate blocks a regression | ⬜ |

## Milestone 6: Talent Search (F1) + Career Coach (F3) ⬜

| Step | Task | Status |
|---|---|---|
| 6.1 | Chroma `candidates` index | ⬜ |
| 6.2 | Search agent (planner + tool calling) | ⬜ |
| 6.3 | 30-query gold set; precision@10 | ⬜ |
| 6.4 | Coach agent (generate → critic → revise) | ⬜ |
| 6.5 | 20-case adversarial set | ⬜ |
| 6.6 | `/search` and `/coach` routes | ⬜ |

| # | Exit criterion | Status |
|---|---|---|
| 6-A | M10: precision@10 ≥ 0.70 | ⬜ |
| 6-B | Coach: 0 unsupported claims | ⬜ |
| 6-C | Degradation without the LLM | ⬜ |
| 6-D | Cached repeats make 0 LLM calls | ⬜ |

## Milestone 7: Next.js web app + live demo ⬜

| Step | Task | Status |
|---|---|---|
| 7.1 | Scaffold `web/`; typed client; server-side key | ⬜ |
| 7.2 | Pages | ⬜ |
| 7.3 | Evidence highlighting | ⬜ |
| 7.4 | Demo mode (cached samples) | ⬜ |
| 7.5 | Deploy (backend host + Vercel) | ⬜ |

| # | Exit criterion | Status |
|---|---|---|
| 7-A | Every page works on the hosted API | ⬜ |
| 7-B | Samples make 0 Gemini calls | ⬜ |
| 7-C | API key never reaches the browser | ⬜ |
| 7-D | Usable at 375 px | ⬜ |

## Milestone 8: Polish & v1.0 release ⬜

| Step | Task | Status |
|---|---|---|
| 8.1 | Final evaluation on the test split | ⬜ |
| 8.2 | Evaluation page | ⬜ |
| 8.3 | README with GIF and diagram | ⬜ |
| 8.4 | CHANGELOG, `demo.sh`, v1.0.0 | ⬜ |
| 8.5 | Optional runner-up feature | ⬜ |

| # | Exit criterion | Status |
|---|---|---|
| 8-A | Clean-machine install | ⬜ |
| 8-B | Results public with git SHA | ⬜ |
| 8-C | Docs current | ⬜ |

---

## Metrics scoreboard

| # | Metric | Target | Latest | Measured in |
|---|---|---|---|---|
| M1 | Parsing F1 | ≥ 0.85 (≥ 0.95 contact) | rules-only val: 0.463 (contact 1.00); 8 val with Gemini (old prompt): 1.000; full val: pending | Milestone 2 |
| M2 | Normalization P / R | ≥ 0.90 / ≥ 0.85 | not measured | Milestone 3 |
| M3 | NDCG@10 / Spearman ρ | ≥ 0.80 / ≥ 0.60 | not measured | Milestone 4 |
| M4 | API completeness | 100% | not measured | Milestone 5 |
| M5 | Reliability | 0 5xx at ~10 users | not measured | Milestone 5 |
| M6 | Latency p95 / p50 | < 10 s / < 5 s | not measured | Milestone 5 |
| M7 | Hallucination rate | ≤ 5% | 8 val with Gemini (old prompt): 0/222 = 0.0%; full val: pending | Milestone 2 |
| M8 | Fairness Δ mean / max | ≤ 0.02 / ≤ 0.05 | not measured | Milestone 4 |
| M9 | Fine-tuning gain | ≥ +2 pts recall | not measured | Milestone 3 |
| M10 | Search precision@10 | ≥ 0.70 | not measured | Milestone 6 |

## Decisions so far

| ADR | Decision | Date |
|---|---|---|
| [ADR-0001](../docs/decisions/ADR-0001-taxonomy-sources.md) | Taxonomy from O\*NET 31.0 + Wikidata + curated layer | 2026-10-03 |
| [ADR-0002](../docs/decisions/ADR-0002-phase1-generators-without-llm.md) | Phase 1 data without LLM; rubric-labeled match gold | 2026-10-03 |
| [ADR-0003](../docs/decisions/ADR-0003-portfolio-rescope.md) | Portfolio re-scope: web app, demo, F1–F5; Celery and infra removed | 2026-10-13 |
| [ADR-0004](../docs/decisions/ADR-0004-external-and-real-world-data.md) | Keep synthetic data; add reworded, real, external and USAJOBS supplements | 2026-10-13 |
| [ADR-0005](../docs/decisions/ADR-0005-line-referenced-extraction.md) | Long text extracted by line reference; how M7 is counted; compact LLM output (proposed; amended 2026-10-15) | 2026-10-13 |
