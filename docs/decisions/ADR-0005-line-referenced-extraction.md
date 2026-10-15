# ADR-0005: Long resume text is extracted by line reference

- **Status:** Proposed (implemented in Milestone 2; owner to confirm)
- **Date:** 2026-10-13
- **Supersedes:** nothing. Refines plan §6.1 steps 5–6 and how M7 is counted. Recorded as plan
  §14 D20.

## Context

Plan §6.1 has the LLM return every field with a verbatim `evidence` span, which the verifier
then aligns against the source (F2). For short fields (a name, a company, a date range) that is
cheap. For long free text it is not:

- The summary, every job bullet and every project description would be copied twice (value and
  evidence), or at least once in full. A typical resume has 10–15 bullets, so this is most of
  the output tokens, and output tokens drive latency. Exit criterion 2-F asks for p95 < 7 s.
- Copied text drifts: models quietly fix typos, merge bullets or paraphrase, which is exactly
  the behaviour F2 exists to catch, but for these fields the copy itself is the only thing we
  need.

## Decision

1. The LLM sees the resume with every content line numbered (`12| Led a team of five`).
2. For the **summary, experience bullets and project descriptions**, it returns line numbers
   (`summary_lines`, `bullet_lines`, `description_lines`). The parser copies those lines from
   the source and groups wrapped lines into bullets by their bullet markers.
3. **Short fields** (name, location, titles, companies, institutions, degrees, skills,
   certification names, verbatim date text) are still returned as text and verified by
   rapidfuzz alignment at ≥ 90, with confidence halved on failure (plan §6.1 step 6, unchanged).
   Normalized dates are re-derived from the verbatim date text by the date rules.
4. **M7 counting:** text copied by line reference is grounded by construction and is *not*
   counted in the M7 denominator. A reference to a line that does not exist counts as one
   checked, unverified field. M7 = unverified ÷ checked over the short fields plus invalid
   references. The ≤ 5% target is unchanged.

### Amendment (2026-10-15): compact LLM output

The first real calls (`gemini-3.8-flash`, thinking `low`, 8 val resumes) were perfectly accurate
(M1 F1 1.000 over 443 fields, 0 unverified of 222) but slow: 837–1,325 output tokens at about
90 tokens/s gave parse latencies of 7.4–19.3 s (p50 12.7 s). There were no thinking tokens, so
latency is output size. The output was therefore cut to what the parser cannot derive:

5. Line references are **inclusive ranges** (`[[27, 33]]`), not lists of numbers.
6. Dates come back **only as verbatim text**; the date rules normalize them (start, end,
   current). Unparseable date text leaves the dates empty rather than trusting the model.
7. **No model-reported confidence.** It was 0.95 on every item, so it carried no information.
   LLM values start at a fixed prior (0.9), which the verifier halves when the evidence is not
   found; the plan's "every field carries confidence" now means the parser assigns it.
8. Skills already listed under a skills header are a **rule hint** and are not repeated; the
   model returns only additional skills. `category_hint` of section skills is `unknown` until
   the Normalization Agent (Milestone 3) categorizes them from the taxonomy.
9. Per-role `skills_mentioned` is **derived**: the resume skills named in that role's bullets.
10. The prompt asks for **minified JSON**: Gemini's `count_tokens` showed the same extraction is
    365 tokens minified versus 642 indented, and the model was emitting it indented.

Measured on one resume after 5–9 (before 10): 1,225 → 616 output tokens, 11.0 → 6.8 s.

## Consequences

- Fewer output tokens and less latency per resume; long text in the API output is exactly the
  resume's text (including its typos), which is what evidence highlighting in the web app needs.
- M7 measures what can actually be hallucinated. Excluding pointer fields makes the rate
  *higher* (stricter) than counting them as automatically verified would.
- The model can still point at the wrong lines. That is an accuracy error, measured by M1
  (`experience.responsibilities`, `summary`, `projects.description`), not a hallucination.
- The `ResumeExtraction` schema (LLM output) and `ParsedResume` (API output) differ more than
  before; `merge.py` maps one to the other and is unit-tested.
- Recorded fixtures are keyed by the exact prompt. The prompt is **frozen** from 2026-10-15 so
  the daily free-tier recordings (20 requests/day) accumulate; changing it means re-recording.
