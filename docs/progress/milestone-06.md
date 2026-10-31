# Milestone 6 Progress Record: Talent Search (F1) + Career Coach (F3)

**Status:** Completed & Verified  
**Date:** 2026-10-31  
**Target Exit Criteria:** 6-A, 6-B, 6-C, 6-D (All Passed)

---

## 1. Overview & Architecture

Milestone 6 delivered the two advanced AI agents in the TalentGraph architecture:
1. **Talent Search Agent (`talentgraph.agents.search`, Feature F1):**
   - Natural language candidate search driven by structured `SearchPlan` (must/should skills, min years, domain, seniority).
   - LangGraph tool-calling loop (resolving skills, hard filtering, semantic retrieval over Chroma/NumPy vector index, and match scoring with evidence citations).
   - Deterministic rule-based query parser fallback (`keyword_plan`) for zero-downtime offline execution.
   - High performance candidate vector store (`CandidateIndex`) pre-indexed with 560 candidate profiles (`data/.checkpoints/candidates_embedded.npz`).
2. **Career Coach Agent (`talentgraph.agents.coach`, Feature F3):**
   - Candidate gap analysis and action planning:
     - Learning plan ordered topologically by taxonomy prerequisite and relation edges.
     - 5 targeted interview questions aimed at weakest requirements.
     - Up to 5 resume bullet rewrites grounded strictly in existing evidence.
   - Multi-stage factuality critic (`critic.py`):
     - Stage 1 (Deterministic): rejects unevidenced skills, fabricated metrics/numbers, and non-taxonomy learning goals.
     - Stage 2 (LLM): verifies subtle hallucinations (invented employers, unverified achievements).
     - Subgraph feedback loop: `generate -> critic -> revise -> critic` (max 2 revisions), dropping any persistent unsupported claims and logging them in `removed_claims`.
3. **API & Endpoints:**
   - `POST /api/v1/search`: Returns ranked candidate hits with evidence citations and query execution metadata.
   - `POST /api/v1/coach`: Returns verified coaching report.
   - Resilient degradation: with no LLM, `/search` returns `status="partial"` from keyword planner; `/coach` returns 503 problem+json (`application/problem+json`).
   - Query & candidate cache: repeat requests make 0 LLM calls.

---

## 2. Exit Criteria Verification

| Exit Criterion | Check | Pass Condition | Result | Status |
|---|---|---|---|---|
| **6-A** | **Metric M10** | Precision@10 $\ge$ 0.70 on the search gold set | **0.9000** (MRR: 0.9833) | **PASSED** |
| **6-B** | **Coach Critic** | 0 unsupported claims in final outputs on the adversarial set; every removed claim listed in report | **0 unsupported claims** (20/20 baits caught and listed) | **PASSED** |
| **6-C** | **Degradation** | With no LLM, `/search` returns `partial` from keyword planner; `/coach` returns 503 problem+json (not 500) | Verified via e2e API tests (`test_search_endpoint_degradation_partial`, `test_coach_endpoint_degradation_503_problem_json`) | **PASSED** |
| **6-D** | **Quota / Cache** | Repeat request for same query or candidate+job makes 0 LLM calls (cache test) | Verified via unit & e2e cache tests (`test_search_agent_cache_exit_criterion_6_d`, `test_coach_endpoint_cache_and_report`) | **PASSED** |

---

## 3. Detailed Results

### 3.1 Metric M10: Search Precision@10 (`eval/search.py`)
- Evaluated on `data/eval/search_gold.json` (30 recruiter queries across diverse industries: software, data, finance, healthcare, legal, sales, education).
- **Mean Precision@10:** `0.9000` (Requirement: $\ge 0.70$).
- **Mean Reciprocal Rank (MRR):** `0.9833`.
- Evaluation reports generated:
  - `reports/search_precision_20261031_091221.json`
  - `reports/search_precision_20261031_091221.md`

### 3.2 Coach Adversarial Factuality Evaluation (`eval/coach.py`)
- Evaluated on `data/eval/coach_adversarial.json` (20 adversarial cases spanning fabricated metrics, hallucinated companies, unverified skills, and non-existent taxonomy goals).
- **Unsupported Claims in Final Output:** `0` (Requirement: 0).
- **Total Removed Claims Recorded:** `20`.
- Evaluation reports generated:
  - `reports/coach_adversarial_20261031_092007.json`
  - `reports/coach_adversarial_20261031_092007.md`

### 3.3 Test Suite Execution
- **Unit & Integration Suite:** 300 tests passed, 0 failures (`uv run pytest`).
- **Code Quality:**
  - `uv run ruff check .` passed with 0 errors.
  - `uv run ruff format --check .` passed (156 files formatted).
  - `uv run mypy src/talentgraph` passed with 0 errors across 84 source files.

