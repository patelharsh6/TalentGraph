# ADR-0004: Add real-world and external data next to the synthetic corpus

- **Status:** Accepted
- **Date:** 2026-10-13
- **Supersedes:** nothing. Extends plan §10.1. Recorded as plan §14 D19.

## Context

The Phase 1 datasets are synthetic (ADR-0001, ADR-0002). They have exact field-level labels, a
clean license and byte-for-byte reproducibility, and they are safe to send to the Gemini free
tier. They also have three known weaknesses:

1. **Template text is clean and repetitive**, so M1 is likely optimistic on real resumes.
2. **The match gold is circular** with respect to skill overlap (ADR-0002).
3. **The job descriptions are generated**, so they are tidier than real postings.

The owner asked whether to replace the corpus with a dataset from the internet. Replacing it was
rejected for four reasons:

- Public resume datasets have category labels, not the field-level labels M1 needs.
- They contain real personal data, which must not be sent to the free tier (plan §3.1).
- Many are scraped, with unclear licenses.
- No public dataset has expert-graded candidate–job scores.

Instead, targeted additions cover each weakness.

## Decision

The synthetic corpus stays the **primary** train/val/test set. Every M1–M10 target is measured
on it. Five additions are reported **next to** those results:

| # | Addition | Source and license | Use | Step |
|---|---|---|---|---|
| A | **LLM-reworded resumes**: Gemini rewrites summaries and experience bullets of a subset of the synthetic profiles. Ground-truth fields (names, dates, companies, skills) are kept, and the rewrite is validated against them | Our own synthetic data, so the free tier is allowed | A harder variant of the val/test splits; M1 reported on both | 2.14 |
| B | **Real-resume check set**: 10–20 resumes from the owner and people who give **written consent**, including consent to processing by the Gemini free tier. Key fields are labeled by hand | Private; **never committed** (`data/private/`, gitignored) | A "real-world M1" figure, report-only (no target, no tuning) | 2.15 |
| C | **Match-gold re-validation**: an LLM judge on a sample, or ~200 human-graded pairs with κ | Our own | Required by ADR-0002 before Milestone 4 sign-off | 4.9 |
| D | **External skill benchmark**: TechWolf `skill-extraction-techwolf`, `-tech` and `-house` (Hugging Face). Job-posting sentences with skill spans labeled with ESCO v1.1.0 skills; `-tech` and `-house` extend the SkillSpan TECH and HOUSE subsets | **CC BY 4.0** (all three dataset cards). Cite Decorte et al. 2023, arXiv:2307.10778 | External check of normalization (M2) and the fine-tuning gain (M9), report-only | 3.11 |
| E | **Real job postings**: (1) about 100 IT and data postings from the **USAJOBS API**, with full text, credited to USAJOBS and unmodified in storage; (2) `lukebarousse/data_jobs` on Hugging Face, which holds job titles and extracted skill lists only | (1) USAJOBS Terms of Service. OPM permits public reuse with credit and unchanged values; data comes through the owner's registered key. (2) **Apache-2.0** | (1) JD-parser robustness and demo jobs. (2) Unrecognized-skill rate on real skill strings | 3.11, 4.11 |

**ESCO crosswalk for D.** Our taxonomy is O\*NET + Wikidata, not ESCO. An ESCO label maps to a
taxonomy slug only through exact match on our skill names and aliases. The mapping must **not**
use the normalization cascade, which would make the evaluation circular. A random 100 mappings
are spot-checked by hand. Spans whose ESCO skill has no mapping are left out, and the coverage
share is reported.

**Not used:**
- Scraped LinkedIn, Indeed or Glassdoor datasets, including re-uploads that claim MIT or similar
  licenses: the provenance is doubtful.
- Public resume corpora: no field labels, real personal data, unclear licenses.

## Consequences

- **No metric targets change.** The A, B, D and E results are reported next to M1, M2 and M9
  ("synthetic / reworded / real / external") on the evaluation page. Only the synthetic test
  split decides pass or fail.
- **Free-tier quota:** A spends quota (about 1 call per reworded resume, checkpointed and
  resumable). B uses the free tier only because the consent covers it; without that consent,
  B would need a paid key or rules-only parsing.
- **PII:** B stays out of git and out of `reports/`. Only aggregate scores are published.
- **Attribution:** D and E get a `data/external/ATTRIBUTION.md` (CC BY 4.0 credit, USAJOBS
  credit), and the evaluation page credits them too. The downloaders pin dataset revisions so
  results are reproducible. Raw downloads are gitignored like the O\*NET tables.
- **Owner actions:** collect the consented resumes for B, and register a USAJOBS API key for E1
  (`USAJOBS_API_KEY`, `USAJOBS_USER_AGENT` in `.env`).
- **Licenses to recheck at download:** the USAJOBS terms are partly contradictory (the API terms
  limit use to the registered requester; OPM's reuse statement permits public reposting with
  credit). Before publishing USAJOBS text in the demo, the owner confirms with
  access@usajobs.gov. Until then, USAJOBS postings are used for evaluation only. Demo jobs stay
  synthetic.
