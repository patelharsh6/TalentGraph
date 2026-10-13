# ADR-0002: Phase 1 datasets generated without LLM calls; match grades from a rubric labeler

- **Status:** Accepted (temporary; revisit before Phase 4 sign-off)
- **Date:** 2026-10-03
- **Supersedes:** plan §14 D6 (in part). Recorded as plan §14 D12.

## Context

ordered.md Phase 1 planned three uses of the Gemini free tier:

- experience bullets for the synthetic profiles (1.6)
- LLM-proposed aliases (1.3)
- an **LLM judge** that grades about 2,000 candidate–job pairs against
  `data/eval/match_rubric.md` (1.10, plan D6)

No `GEMINI_API_KEY` was configured during Phase 1, and the free-tier daily quota would need
several days for the judge alone.

## Decision

- **Profiles:** experience bullets, summaries and projects come from deterministic templates
  (Faker for PII, seeded RNG). No LLM call.
- **Aliases:** none from an LLM (see ADR-0001).
- **Match gold:** `scripts/label_matches.py` grades every pair with a deterministic labeler that
  applies the rubric's thresholds to the ground truth:
  - required-skill share: ≥ 90% / 70% / 40% / 10%
  - experience vs. the job minimum
  - industry alignment

  Selection draws 4 candidates per grade per job and backfills from the least-filled grade.
  `human_labeling.csv` exports 240 pairs with an **empty** `human_grade` column. Earlier output
  pre-filled it from the machine grade and marked it "agreed", which faked agreement.
  `--stats` reports quadratic-weighted Cohen's κ once humans fill it in.

## Consequences

- Phase 1 used no LLM quota, and every dataset is byte-for-byte reproducible (1-I).
- The match gold is **circular with respect to skill overlap**: a matcher that scores
  canonical-skill overlap will agree with it by construction. M3 (NDCG@10, Spearman ρ) measured
  against this gold therefore overstates quality. Before Phase 4 sign-off, either:
  1. run the LLM judge (same rubric, different model from the matcher), or
  2. collect the human labels for `human_labeling.csv` and report κ.

  Phase 4 must report which one was used.
- Template-generated resume text is less varied than LLM text. Phase 2 parsing metrics (M1) on
  this corpus may be optimistic; real or LLM-varied resumes should be added when quota allows.
- No metric target is lowered by this ADR.
