# ADR-0006: Parser latency target (2-F) is p95 < 10 s on the free tier

- **Status:** Accepted (owner decision, 2026-10-19)
- **Date:** 2026-10-19
- **Supersedes:** the "parser p95 < 7 s" part of exit criterion 2-F (`ordered.md`). The cache-hit
  target (< 200 ms) and M6 (`plan.md` §2) are unchanged. Recorded as plan §14 D22.

## Context

Exit criterion 2-F asks for a parser p95 below 7 s over 20 sequential val resumes with the real
API. ADR-0005 and its amendment cut the LLM output to what the parser cannot derive (line
ranges, verbatim dates only, no model confidence, minified JSON). That took the old prompt's
p95 from 19.3 s down, but the frozen prompt still misses 7 s on `gemini-3.8-flash` (free tier,
thinking `low`):

| Sample | n | p50 | p95 | max |
|---|---|---|---|---|
| 2-F sample: first 20 real calls (`eval.latency --fake --from-records`) | 20 | 4.3 s | **8.0 s** | 9.5 s |
| All real calls with the frozen prompt (2026-10-17, 10-19) | 38 | 4.4 s | 9.5 s | 35.8 s |

In the 2-F sample the LLM call accounts for 7.9 s of the 8.0 s p95; extraction, merge and
verification take under 0.1 s. The slow calls are not the long resumes: the tail (15.0 s and
35.8 s on two ordinary resumes) is server time on a shared free tier that also returned 503s on
about half the calls on 2026-10-15. Little is left to cut on our side. The output is already
minimal, and a client-side deadline at 7 s would push about 1 parse in 8 to the rules-only
`partial` result (rules-only val F1 0.463).

## Decision

1. 2-F's parser target becomes **p95 < 10 s** on the same sample (20 sequential val resumes,
   real API, timed without pacing waits). That matches M6's p95, the plan-level end-to-end
   target.
2. The cache-hit target (< 200 ms) is unchanged.
3. M6 itself (`POST /parse` end to end: p95 < 10 s, p50 < 5 s) is unchanged and is still
   measured in Milestone 5.

## Consequences

- 2-F passes on the recorded sample (p95 8.0 s; cache hit p95 0 ms).
- **M6 has no headroom.** The parser alone may use most of the 10 s, so normalization (Milestone
  3) must keep its LLM disambiguation off the common path, and Milestone 5 may still miss M6 at
  the tail. If it does, the options are the same as here: a paid key, a smaller/faster model, or
  an ADR for M6. This ADR does not pre-approve any of them.
- The 38-call p95 (9.5 s) is close to 10 s. The latency numbers in the portfolio write-up must
  name the free tier and report the tail honestly.
