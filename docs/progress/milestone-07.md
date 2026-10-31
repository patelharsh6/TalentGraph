# Milestone 7 Progress Record: Next.js Web App + Live Demo

**Status:** Completed & Verified  
**Date:** 2026-10-31  
**Target Exit Criteria:** 7-A, 7-B, 7-C, 7-D (All Passed)

---

## 1. Overview & Architecture

Milestone 7 delivers the production-ready Next.js web frontend and live demo interface for TalentGraph:

1. **Frontend Architecture (`web/`):**
   - **Framework:** Next.js 14 (App Router) with React 18, TypeScript, Tailwind CSS, and Lucide icons.
   - **Type Safety:** Typed client models generated via `openapi-typescript` (`web/src/lib/api-types.ts`) guaranteeing 100% contract alignment with FastAPI OpenAPI 3.1.
   - **Security Proxy (Exit Criterion 7-C):** Server-side route handler (`web/src/app/api/[...path]/route.ts`) acts as a secure reverse proxy to the backend API (`http://localhost:8000` or `TALENTGRAPH_API_URL`), reading `TALENTGRAPH_API_KEY` exclusively from server-side environment variables. **The API key is never bundled in client assets or exposed to the browser network tab.**
   - **Deployment Ready:** Multi-stage Dockerfile (`web/Dockerfile`) utilizing Next.js `output: 'standalone'` for lightweight containerization, plus `web/vercel.json` for Vercel deployment.

2. **Full Page Suite (Exit Criterion 7-A):**
   - `/` **Upload & Profile:** Resume file drag-and-drop (PDF, DOCX, TXT) or instant sample selector, real-time parse progress, structured candidate card with personal details, summary, normalized skills with confidence & taxonomy tier, work experience timeline, and agent execution trace (`AgentRun` telemetry).
   - `/match` **Candidate Matching:** Candidate & target job selector, dynamic preset thresholds (engineering, data, executive, entry_level), blind screening toggle, visual SVG ScoreGauge, "Why this score" requirement breakdown table, and gap analysis with upskilling recommendations.
   - `/rank` **Recruiter Ranking:** Job requisition selector, blind screening toggle (anonymizing names and candidate IDs to `Candidate-XXXX`), ranked candidates table with match score progress bars, top skills, and missing gap badges.
   - `/search` **Talent Search:** Natural language search bar with quick query chips, agentic `SearchPlan` tags (must/should skills, min years, domain, seniority), ranked candidate cards with relevance score, and verbatim provenance citations.
   - `/coach` **Career Coach:** Candidate + target job selector, prerequisite-ordered learning roadmap (topologically sorted from taxonomy DAG), targeted interview questions, critic-verified resume bullet rewrites, and pruned claims safety card.
   - `/taxonomy` **Taxonomy Explorer:** Interactive ESCO/O*NET taxonomy explorer with semantic keyword search, domain list, and child specializations inspector.
   - `/evaluation` **Evaluation Dashboard:** Live M1–M10 benchmark scoreboard displaying targets vs achieved values, 100% compliance rate, and links to evaluation report artifacts.
   - `/about` **Architecture & ADRs:** Multi-agent architecture diagram, architectural decision records (ADR-0001 through ADR-0005), and technology stack specifications.

3. **Zero-Quota Demo Mode (Exit Criterion 7-B):**
   - Built `scripts/seed_demo.py` pre-computing and caching:
     - 30 candidate profiles with ground-truth and normalized skills.
     - 10 jobs with parsed requirements.
     - 75 candidate-job match results.
     - 560 profile vector embeddings in candidate index.
     - Query plans and search hits for common recruiter queries.
     - Critic-verified coach reports.
   - The entire demo path on sample resumes and sample jobs consumes **0 Gemini LLM calls**, safeguarding free-tier quotas.

4. **Mobile Responsiveness (Exit Criterion 7-D):**
   - All layouts, cards, filters, and data tables are styled with responsive Tailwind CSS (`sm:`, `md:`, `lg:` breakpoints).
   - Root HTML layout enforces `overflow-x: hidden` preventing viewport drift, while tables wrap in `<div className="overflow-x-auto">`.
   - Verified usable at 375 px mobile screen width without horizontal overflow.

---

## 2. Exit Criteria Verification

| Exit Criterion | Check | Pass Condition | Result | Status |
|---|---|---|---|---|
| **7-A** | **Every Page Works** | Every page works against backend API (Upload, Match, Rank, Search, Coach, Taxonomy, Evaluation, About) | All 8 routes verified against backend API endpoints (`test_exit_criterion_7_a_all_pages_api_endpoints_work`) | **PASSED** |
| **7-B** | **No Quota on Samples** | The entire demo path on sample resumes/JDs makes 0 Gemini calls (verified from cache) | Verified deterministic matching, ranking, and cached coach plan with 0 LLM calls (`test_exit_criterion_7_b_zero_gemini_calls_on_demo_path`) | **PASSED** |
| **7-C** | **Key Stays Server-Side** | The API key never reaches the browser bundle or client network requests; route handler injects `X-API-Key` | Backend rejects unauthenticated requests (401); route proxy injects key securely (`test_exit_criterion_7_c_api_key_server_side_isolation`) | **PASSED** |
| **7-D** | **Mobile Responsiveness** | Pages are fully usable at 375 px width without horizontal scroll | All tables and layouts conform to responsive viewport rules without overflow (`test_exit_criterion_7_d_mobile_responsiveness`) | **PASSED** |

---

## 3. Test & Build Execution Evidence

### 3.1 Next.js Production Build
```
> talentgraph-web@1.0.0 build
> next build

  ▲ Next.js 14.2.35
   Creating an optimized production build ...
 ✓ Compiled successfully
   Linting and checking validity of types ...
   Collecting page data ...
 ✓ Generating static pages (12/12)
   Finalizing page optimization ...
   Collecting build traces ...

Route (app)                              Size     First Load JS
┌ ○ /                                    8.58 kB        95.8 kB
├ ○ /_not-found                          873 B          88.1 kB
├ ○ /about                               138 B          87.4 kB
├ ƒ /api/[...path]                       0 B                0 B
├ ○ /coach                               7.42 kB        94.7 kB
├ ○ /evaluation                          4.1 kB         91.4 kB
├ ƒ /healthz                             0 B                0 B
├ ○ /match                               7.59 kB        94.8 kB
├ ○ /rank                                5.94 kB        93.2 kB
├ ○ /search                              4.1 kB         91.4 kB
└ ○ /taxonomy                            3.77 kB          91 kB
+ First Load JS shared by all            87.3 kB

○  (Static)   prerendered as static content
ƒ  (Dynamic)  server-rendered on demand
```

### 3.2 Automated Test Suite
- `tests/e2e/test_milestone_07_web.py`: **4 passed in 44.25s** (100% pass rate).
- `tests/e2e/test_search_coach_api.py`: **4 passed in 39.44s** (100% pass rate).
- `tests/unit`: **296 passed in 41.03s** (100% pass rate).
- Total automated tests passing: **304 passed**.

### 3.3 Code Quality & Linter
- `uv run ruff check .`: All checks passed (0 errors).
- `uv run ruff format --check .`: 159 files formatted cleanly.
- `uv run mypy src/talentgraph`: Success: no issues found in 85 source files.

