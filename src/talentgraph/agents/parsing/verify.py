"""Step 2.10: evidence verifier; aligns each LLM evidence span to the source text (feature F2).

Every LLM-extracted value carries an `evidence` span that should appear verbatim in the resume.
The span is aligned against the source with rapidfuzz `partial_ratio` (after normalizing case,
whitespace, dashes and quotes, so PDF line wraps and typography don't count as differences):

- score ≥ 90: `verified = True`;
- otherwise `verified = False` and the confidence is halved. The share of such fields is the
  hallucination rate (M7).

Values from deterministic rules are verified when they are extracted and are skipped here.
"""

import re
import unicodedata
from collections.abc import Iterator
from dataclasses import dataclass, field

from pydantic import BaseModel
from rapidfuzz import fuzz

from talentgraph.core.schemas.resume import Grounded, ParsedResume

VERIFY_THRESHOLD = 90.0
UNVERIFIED_PENALTY = 0.5
_TRANSLATE = str.maketrans(
    {"–": "-", "—": "-", "‐": "-", "‑": "-", "−": "-", "‘": "'", "’": "'", "“": '"', "”": '"'}
)


def normalize_for_alignment(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).translate(_TRANSLATE).casefold()
    return re.sub(r"\s+", " ", text).strip()


class EvidenceAligner:
    """Scores evidence spans against one source document."""

    def __init__(self, source_text: str) -> None:
        self._source = normalize_for_alignment(source_text)

    def score(self, evidence: str) -> float:
        span = normalize_for_alignment(evidence)
        if not span or not self._source:
            return 0.0
        if span in self._source:
            return 100.0
        return float(fuzz.partial_ratio(span, self._source))


@dataclass
class VerificationReport:
    checked: int = 0
    unverified: int = 0
    failures: list[str] = field(default_factory=list)  # evidence spans that were not found

    @property
    def hallucination_rate(self) -> float:
        return self.unverified / self.checked if self.checked else 0.0


def iter_grounded(node: object) -> Iterator[Grounded]:
    """Every value with provenance in a model tree, depth first."""
    if isinstance(node, Grounded):
        yield node
    if isinstance(node, BaseModel):
        for name in type(node).model_fields:
            yield from iter_grounded(getattr(node, name))
    elif isinstance(node, list):
        for item in node:
            yield from iter_grounded(item)


def verify_resume(
    resume: ParsedResume,
    source_text: str,
    *,
    threshold: float = VERIFY_THRESHOLD,
    extra_unverified: int = 0,
) -> VerificationReport:
    """Check every not-yet-verified value in place and record the counts in `resume.meta`.

    `extra_unverified` counts LLM output that could not even be turned into a field, such as a
    reference to a line number that does not exist; it counts as checked and unverified.
    """
    aligner = EvidenceAligner(source_text)
    report = VerificationReport(checked=extra_unverified, unverified=extra_unverified)
    for item in iter_grounded(resume):
        if item.verified is not None:
            continue  # rules output, or already checked
        report.checked += 1
        if item.evidence and aligner.score(item.evidence) >= threshold:
            item.verified = True
            continue
        item.verified = False
        item.confidence = round(item.confidence * UNVERIFIED_PENALTY, 4)
        report.unverified += 1
        report.failures.append(item.evidence or "<no evidence>")
    resume.meta.llm_field_count = report.checked
    resume.meta.unverified_count = report.unverified
    return report
