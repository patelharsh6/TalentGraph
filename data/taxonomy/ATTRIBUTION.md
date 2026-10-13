# Taxonomy sources and attribution

The TalentGraph skill taxonomy (`skills.csv`, `aliases.csv`) is built by
`scripts/build_taxonomy.py` from the sources below. See ADR-0001
(`docs/decisions/ADR-0001-taxonomy-sources.md`) for why these sources were chosen.

## 1. O\*NET 31.0 Database

- **Publisher:** U.S. Department of Labor, Employment and Training Administration (USDOL/ETA)
- **Files used:** `software_skills.csv` (Software Skills: workplace product examples and their
  category) and `content_model_reference.csv` (names and descriptions of Knowledge, Essential
  Skills and Transferable Skills elements)
- **Download:** `uv run python data/taxonomy/raw/download.py` (pinned to release 31.0 by
  SHA-256; files land in the gitignored `data/taxonomy/raw/onet/`)
- **License:** [Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/)
- **Used for:** about 8,640 level-3 software skills and 134 software categories, plus O\*NET
  knowledge areas and essential/transferable skills. O\*NET product names become `onet` aliases;
  derived spellings (vendor-stripped, acronym, punctuation forms) become `variant` aliases.
- **Changes made:** names are HTML-unescaped; each product is filed under the software category
  in which O\*NET lists it most often; products that duplicate a curated skill are merged into it
  as aliases; descriptions are generated from the category and occupation counts.

Required attribution:

> This taxonomy includes information from the O\*NET 31.0 Database by the U.S. Department of
> Labor, Employment and Training Administration (USDOL/ETA). Used under the CC BY 4.0 license.
> O\*NET® is a trademark of USDOL/ETA. TalentGraph has modified all or some of this information.
> USDOL/ETA has not approved, endorsed, or tested these modifications.

## 2. Wikidata

- **Source:** English alternative labels (`skos:altLabel`) of Wikidata items that are software
  (Q7397) or programming languages (Q9143), matched to taxonomy skills by exact English label
- **Snapshot:** `data/taxonomy/wikidata_aliases.csv`, written by
  `scripts/fetch_wikidata_aliases.py` (committed so the build is reproducible offline)
- **License:** [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) (no attribution
  required; credited here anyway)
- **Used for:** `wikidata` aliases (for example `Postgres`, `GNU R`). Alt-labels that are
  descriptions rather than names are filtered out.

## 3. Hand-curated layer (TalentGraph)

- The domain → category → subcategory skeleton and about 700 modern technology, business,
  soft-skill and domain skills defined in `scripts/build_taxonomy.py`
- `curated_tech.yaml`: about 150 additional technologies and their aliases
- `aliases_curated.yaml`: high-precision abbreviations (`JS`, `TS`, `K8s`, `TF`, `GCP`, `AWS`,
  `ML`, `NLP`, `CI/CD`, `PM`, `UX`, `Postgres`, and so on), with ambiguity flags
- `implications.yaml` and `relations.yaml`: skill inference rules and prerequisite/related edges

## Not used

- **ESCO** was planned (plan §14 D5) but is not used: its bulk download is behind a manual
  request form, so it can't be fetched reproducibly by a script. ADR-0001 records this.
- **LLM-proposed aliases** (ordered.md 1.3) were not generated: no Gemini quota was available
  in Phase 1. No alias in `aliases.csv` has `source=llm`.
