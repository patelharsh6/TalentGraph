# Phase 01: Data foundation (taxonomy & datasets): progress record

- **Completed by:** Claude Code (agent) for the owner   **Date:** 2026-10-03   **Git SHA:** uncommitted (on top of `88dff78`)
- **LLM quota used:** 0 requests. Every generator is deterministic; there was no Gemini key (ADR-0002).
- **External downloads:** O\*NET 31.0 `software_skills.csv` and `content_model_reference.csv` (hash-pinned); about 80 Wikidata SPARQL queries for alt-labels, snapshotted once.
- **Status:** ✅ Complete. Human κ is "pending" with the CSV exported, which 1-H explicitly allows. This phase depends on Phase 0, which is 🟨 only for 0-H (CI).

## Exit criteria results

| # | Check | Command run | Result / metric | Pass? |
|---|---|---|---|---|
| 1-A | Taxonomy size | `uv run python scripts/seed.py --taxonomy --stats` (run in the api container; see handoff) | **9,642 skills** (L0 4 / L1 38 / L2 205 / L3 9,395), **15,122 aliases** (onet 8,720, variant 4,412, curated 1,616, wikidata 374), 4 levels, 0 orphans, no cycles. Prints `Exit criterion 1-A: PASS`. No placeholder skills (a regression test guards this) | ✅ |
| 1-B | Taxonomy integrity tests | `uv run pytest tests/unit/test_taxonomy_files.py` | `27 passed`: unique slugs; unique normalized aliases that match the normalizer; every alias, implication and relation references an existing slug; parent is exactly one level up; 11 ambiguous words present and flagged | ✅ |
| 1-C | DB and vector parity | seed, then `uv run pytest -m integration` (`tests/integration/test_taxonomy_parity.py`) | Postgres `skills` = 9,642 = Chroma `skills` count. `taxonomy_version` is `2950799ec6a79a4f` in the DB rows, in the Chroma metadata and recomputed from the files. `1 passed` | ✅ |
| 1-D | Required examples resolve | `uv run pytest tests/unit/test_taxonomy_files.py -k required_exact` | `10 passed`: `js→javascript`, `k8s→kubernetes`, `react.js→react`, `ReactJS→react`, `ML Engineering→machine-learning-engineering`, plus ts, tf, gcp, aws and `MS Excel→microsoft-excel` | ✅ |
| 1-E | Resume corpus | `uv run python scripts/render_resumes.py --stats` | **560 resumes**, 0 missing and 0 invalid `.gt.json` (every one validates against `ParsedResume`). 11 industries; 6 templates (~93 each); **PDF 42.0%, DOCX 41.4%**, TXT 16.6%. `Exit criterion 1-E: PASS` | ✅ |
| 1-F | Job corpus | `uv run python scripts/gen_jobs.py --stats`; `pytest tests/unit/test_data_generators.py::test_jobs_corpus` | **120 JDs**, each with a `JobRequirements` gt whose slugs all exist in the taxonomy. Families: engineering 22, data 22, product 11, design 11, cloud 11, finance 11, healthcare 11, marketing 11, manufacturing 10 | ✅ |
| 1-G | Gold sets | `build_normalization_gold.py --stats`; `label_matches.py --stats` | Normalization: **1,200 rows**, **305 hard (25.4%)**, 0 unknown slugs. Match: **2,400 pairs**, grades 0–4 = 25.9 / 25.6 / 26.2 / 12.2 / 10.0%, so **max 26.2% ≤ 40%**. Both print `PASS` | ✅ |
| 1-H | Label quality | hand spot-check of 200 random derived aliases; `label_matches.py --stats` | No LLM aliases exist (no quota), so the spot-check covered the machine-derived `variant` + `wikidata` aliases instead. Round 1: **12 clear + 4 borderline errors / 200 (6–8%)** → 4 bugs fixed (see iteration log). Round 2 (fresh seed): **3 clear + 2 borderline / 200 (1.5–2.5%) ≤ 5%**. Human κ: `Human labels: 0/240 (kappa pending; CSV exported for labeling)` | ✅ |
| 1-I | Reproducibility | `uv run python scripts/regenerate_data.py --check` (deletes every generated output, rebuilds twice, compares SHA-256) | `Files hashed: 1962   differing between runs: 0`, including the PDF and DOCX bytes. `Exit criterion 1-I: PASS` | ✅ |

## Iteration log (metrics phases only)

| Iteration | Change | Metric before → after |
|---|---|---|
| Taxonomy rebuild | Replaced 4,417 placeholder skills and 5,838 fake "llm" aliases with O\*NET 31.0, Wikidata and curated data (ADR-0001) | real skills ≈783 → 9,642; real aliases ≈1.6k → 15,122 |
| Alias spot-check round 1 → 2 | Four fixes: (1) acronym-only forms no longer drive dedupe (a Telvent OMS product had merged into "Opportunity management system OMS"); (2) vendor stripping skips company-name continuations and numbers ("group mt3d99", "50 accounting"); (3) single plain-word vendor-stripped forms are flagged ambiguous ("clinical", "frontier"); (4) only a lowercase plural `s` is stripped from acronyms ("CNS" no longer yields "CN"). O\*NET names are also HTML-unescaped | alias error 6–8% → 1.5–2.5% |
| Match gold balance | Labeler thresholds aligned to `match_rubric.md`; backfill takes from the least-filled grade | max grade share 39.2% → 26.2% |

## Deviations from plan

- **Taxonomy sources (ADR-0001, plan D11):**
  - Built from O\*NET 31.0, Wikidata and the curated layer.
  - ESCO is not used: its bulk download needs a manual form.
  - No LLM-proposed aliases.
  - `curated_tech.yaml` holds about 150 entries, not ≥ 1,500; O\*NET's software list supplies the technical breadth instead.
  - The first build's `ATTRIBUTION.md` claimed ESCO and 1,500+ curated items. Both claims were corrected.
- **No LLM in any generator (ADR-0002, plan D12):**
  - Profile text is template-based.
  - The match gold is graded by a deterministic labeler that applies the rubric, not an LLM judge. M3 must be re-validated with the judge or with human κ before Phase 4 sign-off.
- **Human labeling file:** `human_labeling.csv` used to pre-fill `human_grade` from the machine grade and mark every row "agreed". That is now an empty column (fabricated agreement removed).
- **Normalization gold:** rebuilt.
  - Removed 79 placeholder rows ("Emerging Frontier AI Spec NN"), 320 templated suffix rows and 66 expected slugs that were no longer in the taxonomy.
  - The hard cases are now real: ambiguous terms with context, versions, multi-skill strings (`|`-joined slugs), abbreviations, typos of real skill names, and hand-written unknown skills.
  - Split 50/50 val/test, per ordered.md 1.9.
- **Profiles:**
  - Only `candidate_NNNN.gt.json` is written; the byte-identical `candidate_NNNN.json` copies (560 duplicate files) are gone.
  - Emerging skills carry `canonical_slug: null, emerging: true` instead of invented slugs.
  - 14 profile slugs that were missing from the taxonomy were added as curated skills.
- **Resume renderer rewritten:**
  - The six templates are now genuinely different layouts (two-column and sidebar tables, a grid table, a creative header band).
  - Every gt field is rendered, including certifications and links, which were previously missing from the documents.
  - Missing-section (10%) and section-shuffle (30%) noise is now implemented; the README had claimed it already was. Dropped sections are removed from that resume's gt.
  - The 70/15/15 split is stratified by (industry, template).
  - Output is byte-reproducible (ReportLab `invariant`, fixed DOCX zip timestamps).
- **`seed.py` rewritten:**
  - The old version imported a non-existent `async_session_factory` and swallowed the error, so it had never seeded Postgres.
  - It now does a real idempotent upsert keyed by slug (IDs stable across reseeds: `python` stayed id 258) and prunes stale skills and vectors.
  - It exits non-zero on failure.
- **New scripts:**
  - `regenerate_data.py`: full pipeline, plus the `--check` mode used for 1-I.
  - `fetch_wikidata_aliases.py`: Wikidata snapshot.
  - `data/taxonomy/raw/download.py`: pinned O\*NET download.
- **Fixture sample:** an 18-resume (36-file) sample, 3 per template, is copied to `tests/fixtures/resumes/` (ordered.md 1.11).
- **Git hygiene:**
  - `data/resumes/` and `data/taxonomy/raw/*` are ignored, except `download.py`.
  - Changed files went from 1,386 to 883, all intended for commit: the JSON/CSV/YAML ground truth, scripts, tests, docs and fixtures.

## Known issues / follow-ups

- **Human κ is pending.** Someone needs to fill `data/eval/human_labeling.csv` (`human_grade` 0–4, using `match_rubric.md`). Then run `uv run python scripts/label_matches.py --stats`.
- **LLM judge for the match gold** (ADR-0002): run it when quota allows, or rely on human κ, before Phase 4 sign-off.
- **Narrow alias margin:** 15,122 vs. the 15,000 target. ESCO alt-labels or LLM aliases would widen it.
- **Skewed taxonomy:** level 3 is dominated by O\*NET software products. Watch Phase 3 recall on business and soft skills.
- **Flagging trade-off:** single-word vendor-stripped aliases are conservatively flagged ambiguous. That catches "clinical" and "frontier", but also "photoshop", "essbase" and "hadoop". Phase 3 may want an allow-list.
- **Duplicate relation:** `relations.yaml` has one duplicate edge, so 310 edges in the file become 309 in the DB.
- **Template text:** resume and JD text is template-based, so M1 may be optimistic.

## Handoff notes for the next phase

- **Regenerating data:**
  - `uv run python data/taxonomy/raw/download.py` (once), then `uv run python scripts/regenerate_data.py`.
  - Each data script has `--stats`, which exits 1 if its criterion fails.
  - `data/README.md` documents every file, column and statistic.
- **Seeding** has to run in the api container on this machine (torch is blocked natively):
  `docker compose run --rm --no-deps -v "$PWD/scripts:/app/scripts:ro" -v "$PWD/data/taxonomy:/app/data/taxonomy:ro" api python scripts/seed.py --taxonomy`
- **For Phase 2 (parsing):**
  - Resumes live in `data/resumes/{train,val,test}/`.
  - Each `.gt.json` is the exact ground truth for its document, with dropped sections removed. `meta.template`, `meta.format` and `meta.noise` describe how it was rendered.
  - Dates in documents are noisy formats of the gt's `YYYY-MM`, and some show only the year.
  - Skill strings in documents can contain ~1% typos; the gt keeps the clean `raw`.
  - Unit tests can use `tests/fixtures/resumes/`.
- **For Phase 3 (normalization):**
  - `normalization_gold.csv` expects slug, `NEW`, or `a|b` for multi-skill strings.
  - Use `split=val` for tuning and `split=test` for the M2 report.
  - Use the normalizer in `tests/unit/test_taxonomy_files.py::normalize_alias` (same as `build_taxonomy.normalize_alias_text`).
- **Version:** bump `PIPELINE_VERSION` when parser or normalizer output changes. `taxonomy_version` is now `2950799ec6a79a4f`.
