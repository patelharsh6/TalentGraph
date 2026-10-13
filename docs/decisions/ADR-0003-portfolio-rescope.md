# ADR-0003: Re-scope TalentGraph as an AI-engineering portfolio project

- **Status:** Accepted
- **Date:** 2026-10-13
- **Supersedes:** plan §14 D2 and D8 (Celery), D10 (load-test scale), and plan v1 §1.4 "no front-end UI". Recorded as plan §14 D13–D17.
- **Source:** the planning discussion summarized in [`documents/project-plan-v2.md`](../../documents/project-plan-v2.md), approved by the owner on 2026-10-13.

## Context

The v1 plan (`documents/archive/plan-v1.md`) answered the challenge brief in `idea.md` at
enterprise depth: 12 phases, 7+ Docker services, SDKs in two languages, signed webhooks,
OpenTelemetry tracing and a 50-user load test. The project's real goal is a **portfolio piece
for AI/ML engineering roles**. Its audience is a hiring manager who spends a few minutes on it.
Under v1, that reviewer could only see the work by cloning the repo and running Docker, because
a UI was out of scope. Meanwhile much of the remaining effort went into infrastructure nobody
would see.

## Decision

1. **Add a presentation layer:** a Next.js web app, a hosted live demo, a "why this score" view,
   a recruiter ranking page, a public evaluation page, and a README with a GIF and diagram.
2. **Add five AI features** that show AI-engineering skills:
   - F1: natural-language talent search (agentic RAG, tool calling)
   - F2: grounded extraction, with an evidence verifier and a hallucination metric
   - F3: a Career Coach agent with a critique-and-revise loop
   - F4: blind screening plus a counterfactual fairness audit
   - F5: fine-tuned skill embeddings and a CI gate on eval metrics
3. **Remove** the following:
   - Celery, Flower and webhooks: batches run on FastAPI `BackgroundTasks`.
   - The JS and Python SDK packages: Swagger, cURL and `examples/` replace them.
   - OpenTelemetry, Jaeger and Prometheus: structlog plus `agent_runs` and `?include=trace` remain.
   - The 50-user Locust test, the production compose override and the backup sidecar.
   - The emerging-skill review workflow: unrecognized skills are still detected and listed.
   - API-key scopes and per-key data ownership: one key from `API_KEY`.
   - The custom Redis rate limiter (slowapi replaces it), `Idempotency-Key` and cursor pagination.
   - The cross-process Gemini RPM/RPD limiter and automatic fallback-model switching.
   - Parsing extras: the TF-IDF section classifier, k-means column detection, pdfplumber, the
     gazetteer, publications, and certification expiry and credential ID fields.
   - Model extras: the six-feature proficiency model, and the whole-profile semantic score,
     complexity signals and S/M/L effort estimates in matching.
   - The Spectral / API-contract eval script and Hungarian alignment in the parsing eval.
   - ZIP batch uploads, and every stretch goal except embedding fine-tuning (now F5).
4. **Keep** the following:
   - Redis, as the cache.
   - ChromaDB, as the vector store.
   - The three core agents and LangGraph.
   - The taxonomy and datasets from Phase 1.
   - Metrics M1–M3 and M6, unchanged.
5. **Replace the 12-phase order** with 8 milestones (0–8) in `documents/ordered.md`. Phases 0–1
   become Milestone 0. The v1 documents move to `documents/archive/`.

## Consequences

- **Lowered target:** M5 changes from "≥ 99% success at 50 concurrent users" to "0 5xx responses
  at ~10 concurrent users" (`LLM_MODE=stub`). Without Celery there is no horizontal worker pool,
  and the demo has one user at a time.
- **Partly lowered target:** M4 now covers the v2 endpoint list (§8 of the new plan). The v1
  endpoints for webhooks and emerging-skill review are gone.
- **New targets:** M7 (hallucination rate), M8 (fairness), M9 (fine-tuning gain) and M10 (search
  precision@10). Their values are first estimates. They may be tuned once, by a later ADR, after
  their first measurement.
- **Schema:** migration `0002_portfolio_rescope` makes these changes:
  - drops `webhook_deliveries`, `api_keys` and every `api_key_id` column
  - drops `batch_jobs.callback_url`
  - drops the review columns of `emerging_skills`

  Downgrade restores them, but `api_key_id` comes back nullable.
- **Code removed in Milestone 1:**
  - `worker/`, `api/webhooks.py`, `api/idempotency.py`, `llm/ratelimit.py`,
    `observability/{tracing,metrics}.py`
  - `deploy/`
  - `scripts/create_api_key.py`, `scripts/train_section_clf.py`, `eval/api_contract.py`
  - the Celery, Flower, OpenTelemetry, prometheus-client and pdfplumber dependencies
- **Free-tier exposure grows:** a public demo invites real uploads, and F1 and F3 call the LLM
  per request. The mitigations are a demo mode with cached samples, an upload warning, and
  Redis caches keyed by content hash plus `PIPELINE_VERSION`.
- **Unchanged:** the ADR-0002 requirement still holds. The rubric-labeled match gold must be
  re-validated with an LLM judge or human κ before Milestone 4 sign-off.
