# ADR-0001: Taxonomy built from O\*NET 31.0, Wikidata and a curated layer (not ESCO)

- **Status:** Accepted
- **Date:** 2026-10-03
- **Supersedes:** plan §14 D5 (in part). Recorded as plan §14 D11.

## Context

Plan D5 called for a taxonomy seeded from ESCO and O\*NET, with at least 5,000 skills and
15,000 aliases (exit criterion 1-A). The Phase 1 build that was first submitted reached those
numbers with placeholder data:

- 4,417 of its 5,200 skills were generated filler (`System Software Spec 001`, …)
- 5,838 aliases labeled `source=llm` were templates (`senior TypeScript`, `Kubernetes v2`), not
  LLM output
- neither ESCO nor O\*NET had actually been downloaded

That would have made the Phase 3 normalization metrics (M2) meaningless, so the owner chose to
rebuild the taxonomy from real sources.

## Decision

Build the taxonomy from three layers:

1. **Curated:** the existing hand-written tree (about 780 real skills, kept as is) plus
   `curated_tech.yaml` and `aliases_curated.yaml`.
2. **O\*NET 31.0 (CC BY 4.0):** Software Skills (about 8,750 real products in 134 categories),
   plus Knowledge, Essential Skills and Transferable Skills elements. The files are downloaded by
   a pinned, hash-checked `data/taxonomy/raw/download.py`.
3. **Wikidata (CC0):** English alt-labels of matching software and programming-language items,
   committed as a snapshot (`wikidata_aliases.csv`) for offline reproducibility.

Aliases are real surface forms only: curated forms, O\*NET names, Wikidata alt-labels, and
mechanically derived variants. The variants are punctuation/spacing, vendor-stripped
("Autodesk AutoCAD" → "autocad"), "Microsoft" → "MS", trailing acronyms, and `and`/`&`.

ESCO is **not** used. Its bulk download needs a manual request form, so a script can't fetch
it reproducibly. LLM-proposed aliases are **not** generated, because there was no Gemini quota.

## Consequences

- 1-A passes on real data: 9,642 skills (4 levels) and 15,122 aliases. The alias margin over
  15,000 is small. Adding ESCO alt-labels or LLM aliases later would widen it.
- The level-3 set leans heavily toward software products, because O\*NET Software Skills is the
  largest source. Business, soft-skill and domain coverage comes mainly from the curated layer
  and the O\*NET Knowledge/Skills elements. Phase 3 should watch recall on non-technical skills.
- Vendor-stripped single words that could be ordinary English ("clinical", "frontier") are
  flagged `ambiguous=true`. This also flags some distinctive names ("photoshop", "essbase"),
  which then need context to resolve: a deliberate precision-over-recall trade-off.
- A hand spot-check of 200 random derived aliases first found a 6–8% error rate. The four bugs
  behind it were fixed, and a fresh 200-alias sample then had 1.5–2.5% (≤ 5% target, 1-H).
- To refresh the data: run `data/taxonomy/raw/download.py` (after bumping the pinned version and
  hashes), then `scripts/fetch_wikidata_aliases.py`, then `scripts/regenerate_data.py`. Bump
  `PIPELINE_VERSION` if normalizer output changes.
