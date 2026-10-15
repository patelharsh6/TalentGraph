# Milestone 02: Parsing Agent + grounded extraction (F2): progress record

- **Completed by:** Claude Code (agent)   **Dates:** 2026-10-13, 2026-10-15   **Git SHA:** 8b1bef2 + uncommitted
- **LLM quota used:** `gemini-3.8-flash` free tier, 20 requests/day.
  - 2026-10-13: 20 requests, 0 succeeded (503s with 3× retries, plus availability pings).
  - 2026-10-15: 20 requests, 9 succeeded (10 failed with 503 "high demand", 1 per-minute 429), plus free `count_tokens` calls.
- **Status:** 🟨 In progress. All code is written and tested. The owner chose to stay on the free tier (2026-10-15), so the remaining LLM work runs once a day with `scripts/daily_llm_batch.py` (status.md owner action 9): 88 val fixtures, then 100 rewordings, then the reworded val fixtures. The real-resume set (2.15) waits on the owner.

## Exit criteria results

| # | Check | Command run | Result / metric | Pass? |
|---|---|---|---|---|
| 2-A | Unit tests on `tests/fixtures/resumes/` (6 templates, 3 formats) | `docker compose run --rm tools uv run pytest -q` | **222 passed, 18 skipped**, 46 s, offline. The 18 skips are `test_parsing_recorded.py`, the end-to-end check over recorded Gemini fixtures; each one switches on (and must pass: status ok, F1 ≥ 0.80, ≤ 10% unverified) as soon as its fixture is recorded. Also: `test_parsing_extract.py`, `test_parsing_sections_rules.py`, `test_parsing_agent.py` | ✅ |
| 2-B | M1 on val (F1 ≥ 0.85; ≥ 0.95 name/email/phone) | `uv run python -m eval.parsing --split val [--ids …]` | Rules only (no LLM): F1 0.463, contact fields 1.000. **First 8 val resumes with Gemini** (pre-compact prompt, 2026-10-15): **F1 1.000** (443/443 fields), name/email/phone 1.000. Full val with the frozen prompt: pending daily recording | ⏳ |
| 2-C | M7 ≤ 5%; corrupted fixture flagged | `pytest -k corrupted`; `eval.parsing` | Corrupted extraction (made-up employer, skill) → `verified: false`, confidence halved, quality penalized ✅. **First 8 val resumes: 0 of 222 checked LLM fields unverified (0.0%)**. Full val: pending | 🟨 |
| 2-D | Degradation | `pytest -k "degrade or partial"`, plus live runs | FakeLLM with no fixture, `LLMQuotaExceeded`, `LLMError`, `TimeoutError` → `partial` with name, email, phone, summary and skills. Live: every real 503 and the 429 on 2026-10-15 degraded to `partial` the same way | ✅ |
| 2-E | PNG → 415; 11 MB → 413; scanned PDF → 422 | `pytest -k problem_json` | 415 `unsupported_file_type`, 413 `file_too_large`, 422 `unsupported_content`, all `application/problem+json` | ✅ |
| 2-F | Parser p95 < 7 s (real API, 20 val, sequential); cache hit < 200 ms | `record_llm_fixtures.py` reports; `eval.latency --from-records` | Old prompt, 9 real calls: p50 12.7 s, **p95 19.3 s** ❌. All of it was LLM output time (~90 tokens/s, no thinking tokens), so the output was compacted (ADR-0005 amendment): on the same resume, **1,225 → 616 tokens, 11.0 → 6.8 s**. The prompt now also asks for minified JSON (`count_tokens`: 642 → 365 tokens for the same content). The 20-resume sample with the frozen prompt builds up from the daily runs | ⏳ |
| 2-G | M1 on reworded and real sets; no private data in git | n/a | Reworded: runs after the val fixtures (daily). Real set: owner action 5; the owner asked to keep it pending (2026-10-15). `eval.parsing --private` writes aggregates only, to `reports/private/` (gitignored) | ⏳ |

Extra checks run along the way (not exit criteria):

- **Section detection** matches the rendered sections on 472/472 train+val resumes, and on 560/560 when test is included. Test was run once as a final check; nothing was tuned on it.
- **Rule extractors on val (88):** email, phone, name, location, links and the date-range count are all 88/88. Skills-section items: 668/670 gold skills found. The 2 misses are typos the renderer injected ("Pyhton").
- **Schema:** all 560 `data/profiles/*.gt.json` validate against `ParsedResume` 2.0 without regenerating data.
- Lint, format and mypy (strict) are clean. The 1-B grep for removed features still finds nothing.
- **Docker:** `docker compose build api` succeeds. Inside the image the parser loads the alias index (14,748 entries) and the lexicon (180 variants).

## Iteration log (metrics milestones only)

| Iteration | Change | Metric before → after |
|---|---|---|
| 1 | TXT header hint required ≥ 4 letters, no comma, starts with a letter (`(EHR)` was read as a header) | section mismatches on train+val: 2 → 0 |
| 2 | Skills: stop splitting on " / "; join a section header that wraps over two lines in narrow sidebars | val rule-skill recall 648/670 → 668/670; predictions 686 → 670 |
| 3 | Phones: regex for `001-…` / extension formats `phonenumbers` misses; drop candidates that are date ranges | phone 88/88 on val |
| 4 | First real Gemini calls (v1 schema, 8 val) | M1 1.000, M7 0.0%, but latency p95 19.3 s |
| 5 | Compact LLM output: line ranges, dates only as text, no model confidence, no repeated skills, derived `skills_mentioned` (ADR-0005 amendment) | candidate_0053: 1,225 → 616 output tokens; 11.0 → 6.8 s |
| 6 | Prompt asks for minified JSON; prompt frozen | `count_tokens` of the same output: 642 → 365 (to be confirmed on real calls) |

## Deviations from plan

- **Long text by line reference (ADR-0005, plan §14 D20, proposed).** The LLM returns line references for the summary, bullets and project descriptions. Short fields keep verbatim evidence and alignment. M7 counts short fields plus invalid line references; the target is unchanged.
- **Compact LLM output (ADR-0005 amendment, plan §14 D21, proposed).** Dates come back only as verbatim text, normalized by the rules. Confidence is assigned by the parser (a 0.9 prior, halved if unverified), because the model's was always 0.95. Skills-section items are not repeated by the model, so their `category_hint` is `unknown` until Milestone 3. `skills_mentioned` is derived from the bullets.
- **Prompt file renamed** to `llm/prompts/parse_resume.md`; added `llm/prompts/reword_resume.md` for Step 2.14.
- **New settings:** `LLM_THINKING_LEVEL` (default `low`; `gemini-3.8-flash` rejects `minimal`), `LLM_MAX_ATTEMPTS` (default 3; batch scripts use 1, because every attempt is quota), `MAX_PDF_PAGES`, `PARSE_CACHE_TTL_S`, `CONFIG_DIR`, `TAXONOMY_DIR`. All are in `.env.example`.
- **`tools` compose service (profile `tools`).** Since 2026-10-15, Windows Application Control on the owner's machine also blocks PyMuPDF's `_mupdf.pyd` and the `pytest.exe`/`mypy.exe` launchers. Tests, mypy and every script that parses a PDF run in a Linux uv container with the repo mounted (`docker compose run --rm tools uv run pytest`). CI is unaffected.
- **Dockerfile** copies `data/taxonomy/{skills,aliases}.csv` into the image for the rule-based skill lookup.
- **mypy:** `pymupdf` gets `follow_imports = "skip"`, because its partial inline hints fail strict mode. **pytest:** `pythonpath = ["."]` so tests can use the eval scorer.
- **Eval matching rules** (documented in `eval/parsing.py`): text matches at rapidfuzz ratio ≥ 85, because rendered resumes carry about 1% typos the clean gold lacks; dates match by year, and by month when both sides have one. `location.country`, `skills_mentioned` and `duration_months` aren't scored.
- **2-F sample source:** on 20 requests/day a separate 20-call latency run would cost a full day, so 2-F uses the first 20 successful real calls from the daily recording runs (`eval.latency --from-records`). These are sequential val parses, timed without the pacing waits between calls.

## Known issues / follow-ups

- **Free-tier availability:** on 2026-10-15 about half the calls failed with 503. At ~10 recordings a day the remaining ~230 calls take roughly 3–4 weeks. A paid key would finish them in an hour.
- **2-F risk:** even at 616 output tokens, generation speed varied 65–115 tokens/s, i.e. 5.4–9.5 s. If minified output doesn't land near 365 tokens, p95 may still miss 7 s. That would need an ADR to adjust 2-F (M6, end-to-end p95 < 10 s, is the plan-level target).
- **Alignment threshold on short spans:** one typo in a 9-character span scores 88.9 (< 90). If the model "fixes" a typo in a short company name, that field is flagged unverified.
- Reading order uses top-band peeling when no gutter spans the whole region. A two-column body with a full-width *footer* can interleave columns; watch the real-resume set.

## Handoff notes

- Once a day: `docker compose run --rm tools uv run python scripts/daily_llm_batch.py` (`--status` shows progress and spends nothing). When it reports everything recorded:
  1. `docker compose run --rm tools uv run python -m eval.parsing --split val` (2-B, 2-C).
  2. `docker compose run --rm tools uv run python -m eval.latency --fake --from-records --redis-url redis://redis:6379/0` (2-F: real-API sample plus cache hit; needs the compose stack up).
  3. `docker compose run --rm tools uv run python -m eval.parsing --dir data/resumes/val_reworded --fixtures-dir data/.checkpoints/reworded_llm --label val_reworded` (2-G).
- The prompt is frozen: fixtures are keyed by the exact prompt and extractor output, so any change there means re-recording (and bump `PIPELINE_VERSION` if parser output changes). Superseded fixtures from 2026-10-15 are archived in `data/.checkpoints/fixtures_v1/` and `fixtures_v2/` (gitignored).
