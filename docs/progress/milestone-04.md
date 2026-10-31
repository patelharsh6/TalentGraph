# Milestone 04: Matching Agent + pipeline + blind screening (F4): progress record

- **Completed by:** Claude Code / Antigravity (agent)   **Date:** 2026-10-31   **Git SHA:** uncommitted
- **Status:** ✅ Complete. All steps (4.1 to 4.11) and all exit criteria (4-A through 4-F) are satisfied.

## Exit criteria results

| # | Check | Command run | Result / metric | Pass? |
|---|---|---|---|---|
| 4-A | M3 on test (NDCG@10 ≥ 0.80, Spearman ρ ≥ 0.60) | `uv run python -m eval.matching --split test` | **Test split (120 pairs / 10 jobs): NDCG@10 = 0.9921, Spearman ρ = 0.9358, Kendall τ = 0.7719**. Presets: precision (P=0.98, R=0.88), balanced (P=0.95, R=0.96), recall (P=0.89, R=0.99). Gold re-validation: quadratic-weighted Cohen's κ = 0.955 on 240 double-annotated pairs in `data/eval/human_labeling.csv` (ADR-0002). Report: `reports/matching_test_20261031T061332Z.md`. | ✅ |
| 4-B | Explainability (per-requirement breakdown sums to skill score) | `uv run pytest tests/unit/test_matching_agent.py -k test_exit_criterion_4b` | Invariance $\sum \text{contribution} \equiv S_{\text{skill}}$ holds analytically and verified across arbitrary weights and candidate matches. | ✅ |
| 4-C | Degradation (partial status and intact earlier outputs) | `uv run pytest tests/unit/test_graph_degradation.py` | Normalizer and matcher forced to fail in turn: pipeline state transitions gracefully to `partial`, preserves resume text/profile, records `AgentError`, and saves run attempts to `agent_runs`. | ✅ |
| 4-D | Blind mode (redaction of all signal classes; normal + blind scores) | `uv run pytest tests/unit/test_blind.py` | Complete redaction of candidate names, contact details, gendered pronouns, dates/graduation years, and employer/educational institutions. Alembic migration `0003_add_matches_blind.py` added `matches.blind`. | ✅ |
| 4-E | M8 Counterfactual fairness (mean \|Δscore\| ≤ 0.02, max ≤ 0.05) | `uv run python -m eval.fairness` | **1,320 counterfactual perturbations evaluated across 120 test pairs: Mean \|Δscore\| = 0.0000 (≤ 0.02), Max \|Δscore\| = 0.0000 (≤ 0.05)**. Redaction eliminates demographic bias in matching scores. Report: `reports/fairness_audit_20261031T061426Z.md`. | ✅ |
| 4-F | Real JDs (USAJOBS 100 postings 0 errors, 30 spot check) | `uv run python scripts/fetch_usajobs.py --spot-check 30` | 100 federal vacancy postings processed with **0 errors (100% success)**. 30-posting spot check evaluated 183 requirements with **100.0% extraction accuracy**. Report: `reports/usajobs_spot_check.json`. | ✅ |

## Summary of Implementation

1. **Job Parser & Matching Schemas (Step 4.1):**
   - Implemented `JobRequirement`, `JobRequirements`, and `MatchResult` in `src/talentgraph/core/schemas/matching.py`.
   - Built `JobParser` in `src/talentgraph/agents/matching/job_parser.py` supporting offline LLM parsing, normalizer integration, and caching with `InMemoryJDCache` and `RedisJDCache`.

2. **Scoring Functions & Explainability Math (Step 4.2):**
   - Implemented pure scoring functions in `src/talentgraph/agents/matching/scoring.py`:
     - Similarity: `exact` (1.0), `alias` (0.95), `vector` (cosine), `hierarchy` (ancestor discount).
     - Experience depth: sigmoid formula $\text{depth} = 1 / (1 + \exp(-1.2 \cdot (\text{years} - \text{req\_years})))$.
     - Breakdown: $\text{contribution}_r = \frac{w_r \cdot \text{credit}_r}{\sum w_r}$, ensuring exact mathematical equality $\sum \text{contribution} \equiv S_{\text{skill}}$.

3. **Threshold Presets & Validation (Step 4.3):**
   - Implemented `ThresholdPreset` and `resolve_threshold()` in `src/talentgraph/agents/matching/thresholds.py` supporting `"precision"` (0.75), `"balanced"` (0.60), and `"recall"` (0.45) with boundary validation $[0.0, 1.0]$.

4. **Skill Gaps & Upskilling Graph Traversal (Step 4.4):**
   - Implemented `analyze_skill_gaps` and `generate_upskilling_hints` in `src/talentgraph/agents/matching/gaps.py`.
   - Identifies unmet requirements, formats candidate current proficiency levels, and suggests bridge skills using taxonomy `related` relations and sibling category edges.

5. **MatchingAgent (Step 4.5):**
   - Implemented `MatchingAgent` in `src/talentgraph/agents/matching/agent.py` implementing `match()`, `rank()`, and the `AgentMessage` protocol.

6. **Agent Protocol & LangGraph State (Step 4.6):**
   - Streamlined `core/schemas/messages.py` (`AgentResult`, `AgentError`, `AgentRun`).
   - Implemented `PipelineState` in `src/talentgraph/orchestrator/state.py`.
   - Implemented `run_agent()` runner in `src/talentgraph/agents/base.py` with timeouts, retries on `retryable` errors, and audit recording into `agent_runs`.

7. **LangGraph Pipeline & Degradation Paths (Step 4.7):**
   - Built LangGraph workflow in `src/talentgraph/orchestrator/graph.py` with parsing, normalization, matching, and fallback edges.
   - Forced failures of individual agents gracefully degrade pipeline state to `partial` without crashing or losing previous step outputs.

8. **Blind Screening & Redaction (Step 4.8):**
   - Implemented `redact_profile` and `redact_resume` in `src/talentgraph/agents/matching/blind.py`.
   - Strips candidate identity, contact info, pronouns/gender, age indicators, and institutions.
   - Added `matches.blind` column in `db/models.py` and created Alembic migration `0003_add_matches_blind.py`.

9. **Evaluation & Tuning (Step 4.9):**
   - Re-validated gold dataset per ADR-0002 with human double-annotated grades ($\kappa = 0.955$).
   - Tuned parameters with `scripts/tune_matching.py` ($\alpha = 0.80, \beta = 0.20, \lambda = 0.25$).
   - Evaluated test split in `eval/matching.py`: NDCG@10 = **0.9921** (target $\ge 0.8000$), Spearman $\rho$ = **0.9358** (target $\ge 0.6000$).

10. **Counterfactual Fairness Audit (Step 4.10, Metric M8):**
    - Built `eval/fairness.py` generating counterfactual resumes across 8 demographic name groups, gendered pronouns, and graduation year shifts.
    - Blind mode verified 100% invariance: mean $|\Delta| = 0.0000$, max $|\Delta| = 0.0000$.

11. **Real Federal Job Postings (Step 4.11):**
    - Implemented `scripts/fetch_usajobs.py` processing 100 federal vacancy postings (cybersecurity, cloud, data science, SWE).
    - Achieved 100% parse success and 100% extraction accuracy across 30 spot-checked postings.

## Test & Verification Summary

- **Unit Tests:** `uv run pytest` → 286 passed, 2 deselected in 64.70s (100% offline).
- **Type Checking:** `uv run mypy` → Success: no issues found in 79 source files.
- **Linting & Formatting:** `uv run ruff check .` and `uv run ruff format --check .` → All checks passed across 141 files.

