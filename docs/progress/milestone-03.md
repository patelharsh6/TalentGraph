# Milestone 03: Normalization Agent + fine-tuned embeddings (F5): progress record

- **Completed by:** Claude Code / Antigravity (agent)   **Date:** 2026-10-31   **Git SHA:** uncommitted
- **Status:** ✅ Complete. All steps (3.1 to 3.11) and all exit criteria (3-A through 3-G) are satisfied.

## Exit criteria results

| # | Check | Command run | Result / metric | Pass? |
|---|---|---|---|---|
| 3-A | Required examples (`JS`, `K8s`, `React.js`, `ReactJS`, `ML Engineering`) | `uv run pytest tests/unit/test_normalization_agent.py -k test_exit_criterion_3a` | `js`→`javascript`, `k8s`→`kubernetes`, `react.js`→`react`, `reactjs`→`react`, `ml engineering`→`machine-learning-engineering`. Composite aliases merged. | ✅ |
| 3-B | M2 on test (Precision ≥ 0.90, recall ≥ 0.85) | `uv run python -m eval.normalization --split test` | **Test split (599 mentions): Precision = 0.9702 (97.02%), Recall = 0.9310 (93.10%), F1 = 0.9502**. Latency: 20.89 ms/item. Report: `reports/normalization_test_20261031T041755Z.md` | ✅ |
| 3-C | Hierarchy & implication rules | `uv run pytest tests/unit/test_normalization_agent.py -k test_exit_criterion_3c` | TensorFlow + PyTorch ⇒ Deep Learning (`inferred: true`). Inferred skills never outrank explicit evidence. | ✅ |
| 3-D | Proficiency estimation | `uv run pytest tests/unit/test_normalization_proficiency.py` | Year bands (0-2y→2, 2-5y→3, 5-8y→4, 8+y→5), qualifier wording ("expert in" +1, "familiar with" -1), and skills-only cap at 2 verified. | ✅ |
| 3-E | M9 fine-tuned embeddings gain | `uv run python scripts/finetune_embeddings.py --skip-train` | Fine-tuned `all-MiniLM-L6-v2` with `MultipleNegativesRankingLoss` on (alias, canonical) pairs split by skill. Test recall: 0.9310 → 0.9343 (+0.33 pts), F1: 0.9502 → 0.9520. Saved to `reports/m9_fine_tuning_20261031T042744Z.md`. | ✅ |
| 3-F | Degradation without LLM | `uv run pytest tests/unit/test_normalization_agent.py -k test_exit_criterion_3f` | Ambiguous skills fall back gracefully to curated default candidates or context vectors, and status is `partial`. | ✅ |
| 3-G | External benchmarks (TechWolf, `data_jobs`) | `uv run python -m eval.external --model base` | TechWolf ESCO crosswalk coverage: **86.8%**, Precision: **0.9394**, Recall: **1.0000**, F1: **0.9688**. `data_jobs` unrecognized rate: **3.3%**. Saved to `reports/external_benchmarks_base_20261031T041630Z.md`. | ✅ |

## Summary of Implementation

1. **Schemas & Taxonomy Repository (Step 3.1):**
   - Implemented `NormalizedSkill`, `EmergingSkillMention`, and `SkillProfile` in `src/talentgraph/core/schemas/skills.py`.
   - Implemented `TaxonomyRepository` in `src/talentgraph/db/repositories/taxonomy.py` with alias indexing, parent/ancestor chains, implication rules, and cross-skill relations.

2. **Cleaning & Splitting (Step 3.2):**
   - Implemented `strip_version`, `split_multi_skills`, and `clean_raw_skill` in `src/talentgraph/agents/normalization/clean.py` preserving composite aliases (e.g. `CI/CD`, `HL7 / FHIR`).

3. **Skill Index & Offline Vector Precomputations (Step 3.3):**
   - Precomputed L2-normalized embeddings for all 9,642 canonical taxonomy skills into `data/.checkpoints/skills_embedded.npz`.
   - Implemented `SkillIndex` query helper in `src/talentgraph/embeddings/skill_index.py`.

4. **Normalization Cascade (Step 3.4):**
   - Built 5-step cascade in `src/talentgraph/agents/normalization/cascade.py`:
     `Clean` → `Exact Alias` → `Fuzzy (rapidfuzz token_sort_ratio >= 88)` → `Embedding (cosine >= 0.82, margin >= 0.05)` → `LLM / Disambiguation Map` → `Unrecognized`.

5. **Hierarchy Inference (Step 3.5):**
   - Implemented `infer_hierarchy` in `src/talentgraph/agents/normalization/hierarchy.py` applying implication rules and ancestor chains with discounted confidence. Explicit skills always win over inferred ones.

6. **Proficiency Estimation (Step 3.6):**
   - Implemented `estimate_proficiency` and `merge_date_intervals` in `src/talentgraph/agents/normalization/proficiency.py` calculating level 1-5 from experience durations and qualifier wording.

7. **Emerging Skill Store (Step 3.7):**
   - Implemented `EmergingSkillStore` in `src/talentgraph/agents/normalization/emerging.py` supporting in-memory and PostgreSQL database accumulation with occurrence counts and up to 5 example contexts.

8. **NormalizationAgent (Step 3.8):**
   - Implemented `NormalizationAgent` in `src/talentgraph/agents/normalization/agent.py` turning `ParsedResume` into `SkillProfile`, scoring quality, and adhering to the Agent message protocol.

9. **Evaluation & Tuning (Step 3.9):**
   - Built `eval/normalization.py`. Tuned fuzzy threshold on `val` split to 88.0.
   - Test evaluation passed Exit Criterion 3-B with P=0.9702, R=0.9310, F1=0.9502.

10. **Fine-Tuning Embeddings (Step 3.10):**
    - Built `scripts/finetune_embeddings.py` using `MultipleNegativesRankingLoss` split strictly by skill.
    - Precomputed fine-tuned skill vectors into `data/.checkpoints/skills_embedded_finetuned.npz`.
    - Generated M9 comparison report.

11. **External Benchmarks (Step 3.11):**
    - Built `scripts/fetch_external.py` and `eval/external.py`.
    - Created `data/external/ATTRIBUTION.md` crediting TechWolf (CC BY 4.0) and `data_jobs` (Apache-2.0).
    - Generated ESCO crosswalk (86.8% coverage) and evaluated external metrics.

## Test & Verification Summary

- **Unit Tests:** `uv run pytest` → 266 passed, 2 deselected in 50.35s (100% offline).
- **Type Checking:** `uv run mypy` → Success: no issues found in 79 source files.
- **Linting & Formatting:** `uv run ruff check .` and `uv run ruff format --check .` → All checks passed across 136 files.

