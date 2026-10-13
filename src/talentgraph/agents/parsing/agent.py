"""Step 2.11: ParsingAgent (merge rules and LLM output, validate, score quality, rules-only
degradation).

    bytes ─▶ detect ─▶ extract ─▶ sections ─▶ rules ─▶ LLM ─▶ merge ─▶ verify (F2) ─▶ quality

File problems (`UnsupportedFileType` 415, `FileTooLarge` 413, `UnsupportedContent` 422) are
raised. Everything after extraction degrades instead: an LLM failure, quota exhaustion or an
empty answer gives a rules-only resume with `status="partial"`, and a verifier failure leaves
fields `verified=None`.
"""

import asyncio
import time
from datetime import date
from pathlib import Path
from statistics import fmean
from typing import Literal

import structlog

from talentgraph import PIPELINE_VERSION
from talentgraph.agents.parsing.cache import ParseCache
from talentgraph.agents.parsing.detect import check_size, detect_file_type
from talentgraph.agents.parsing.docx import extract_docx
from talentgraph.agents.parsing.layout import LayoutDocument
from talentgraph.agents.parsing.llm_extract import NumberedLines, llm_extract
from talentgraph.agents.parsing.merge import build_resume
from talentgraph.agents.parsing.pdf import extract_pdf
from talentgraph.agents.parsing.rules import RuleResult, load_alias_index, run_rules
from talentgraph.agents.parsing.sections import Section, detect_sections, load_lexicon
from talentgraph.agents.parsing.text import extract_text
from talentgraph.agents.parsing.verify import iter_grounded, verify_resume
from talentgraph.config import Settings, get_settings
from talentgraph.core.errors import LLMQuotaExceeded, TalentGraphError
from talentgraph.core.ids import sha256_hex
from talentgraph.core.schemas.messages import AgentName, QualityScore
from talentgraph.core.schemas.resume import (
    FileKind,
    ParsedResume,
    ParseResult,
    ResumeExtraction,
    SectionLabel,
)
from talentgraph.llm.client import LLMClient, get_llm

log = structlog.get_logger(__name__)

CORE_SECTIONS: tuple[SectionLabel, ...] = ("experience", "education", "skills")
MISSING_SECTION_PENALTY = 0.1
UNVERIFIED_PENALTY = 0.5


class ParsingAgent:
    name: AgentName = "parser"

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        llm: LLMClient | None = None,
        cache: ParseCache | None = None,
        today: date | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._llm = llm if llm is not None else get_llm(self._settings)
        self._cache = cache
        self._today = today
        self._lexicon = load_lexicon(str(Path(self._settings.config_dir) / "section_lexicon.yaml"))
        self._aliases = load_alias_index(self._settings.taxonomy_dir)

    async def parse(self, data: bytes, filename: str | None = None) -> ParseResult:
        start = time.perf_counter()
        check_size(data, self._settings.max_upload_mb)
        sha = sha256_hex(data)
        if self._cache is not None:
            hit = await self._cache.get(sha)
            if hit is not None:
                hit.cached = True
                hit.latency_ms = _ms(start)
                log.info("parse.cache_hit", sha=sha[:12], latency_ms=hit.latency_ms)
                return hit

        timings: dict[str, int] = {}
        t = time.perf_counter()
        doc, sections, rules = await asyncio.to_thread(self._prepare, data)
        timings["extract_rules"] = _ms(t)

        warnings = list(doc.warnings)
        t = time.perf_counter()
        extraction, lines, llm_warning = await self._extract_with_llm(sections, rules)
        timings["llm"] = _ms(t)
        if llm_warning:
            warnings.append(llm_warning)

        t = time.perf_counter()
        merged = build_resume(rules, sections, extraction, lines, today=self._today or date.today())
        resume = merged.resume
        warnings.extend(merged.warnings)
        try:
            verify_resume(resume, doc.text, extra_unverified=merged.invalid_line_refs)
        except Exception as exc:  # the verifier must never fail a parse (plan §4.2)
            log.warning("parse.verify_failed", error=str(exc))
            warnings.append("Evidence verification failed; fields are unverified.")
        timings["merge_verify"] = _ms(t)

        self._fill_meta(resume, doc, sections)
        quality = quality_score(resume)
        resume.meta.confidence = quality.score
        status = _status(resume, llm_ok=extraction is not None)
        result = ParseResult(
            status=status,
            resume=resume,
            quality=quality,
            latency_ms=_ms(start),
            warnings=warnings,
            timings_ms=timings,
            sha256=sha,
            pipeline_version=PIPELINE_VERSION,
        )
        log.info(
            "parse.done",
            sha=sha[:12],
            file_type=doc.file_type,
            status=status,
            quality=quality.score,
            unverified=resume.meta.unverified_count,
            **{f"{k}_ms": v for k, v in timings.items()},
        )
        if self._cache is not None and status == "ok":
            await self._cache.set(sha, result)
        return result

    # ---------------------------------------------------------------------------------------------

    def _prepare(self, data: bytes) -> tuple[LayoutDocument, list[Section], RuleResult]:
        """CPU-bound part (runs in a worker thread): layout, sections and rules."""
        kind = detect_file_type(data)
        doc = self._layout(kind, data)
        sections = detect_sections(doc, self._lexicon)
        return doc, sections, run_rules(sections, doc.text, self._aliases)

    def _layout(self, kind: FileKind, data: bytes) -> LayoutDocument:
        if kind == "pdf":
            return extract_pdf(data, max_pages=self._settings.max_pdf_pages)
        if kind == "docx":
            return extract_docx(data)
        return extract_text(data)

    async def _extract_with_llm(
        self, sections: list[Section], rules: RuleResult
    ) -> tuple[ResumeExtraction | None, NumberedLines | None, str | None]:
        """The LLM step, or (None, None, warning) when it is unavailable or returns nothing."""
        try:
            extraction, lines = await llm_extract(self._llm, sections, rules)
        except LLMQuotaExceeded:
            log.warning("parse.llm_quota_exceeded")
            return None, None, "LLM quota exhausted; returning rules-only extraction."
        except (TalentGraphError, TimeoutError) as exc:
            log.warning("parse.llm_failed", error=str(exc))
            return None, None, "LLM extraction failed; returning rules-only extraction."
        except Exception as exc:  # e.g. a fixture that no longer validates
            log.warning("parse.llm_error", error=repr(exc))
            return None, None, "LLM extraction failed; returning rules-only extraction."
        if extraction.is_empty():
            return None, None, "LLM returned no data; returning rules-only extraction."
        return extraction, lines, None

    @staticmethod
    def _fill_meta(resume: ParsedResume, doc: LayoutDocument, sections: list[Section]) -> None:
        resume.meta.file_type = doc.file_type
        resume.meta.layout = doc.layout
        resume.meta.pages = doc.pages
        found: list[SectionLabel] = []
        for s in sections:
            if s.label not in found:
                found.append(s.label)
        resume.meta.sections_found = found


def quality_score(resume: ParsedResume) -> QualityScore:
    """Mean field confidence, less a penalty per missing core section and for unverified fields."""
    confidences = [g.confidence for g in iter_grounded(resume)]
    field_confidence = fmean(confidences) if confidences else 0.0
    present = {
        "contact": resume.personal.email is not None or resume.personal.phone is not None,
        "experience": bool(resume.experience),
        "education": bool(resume.education),
        "skills": bool(resume.skills),
    }
    missing = sum(1 for ok in present.values() if not ok)
    checked = resume.meta.llm_field_count
    unverified_share = resume.meta.unverified_count / checked if checked else 0.0
    score = (
        field_confidence
        * (1 - MISSING_SECTION_PENALTY * missing)
        * (1 - UNVERIFIED_PENALTY * unverified_share)
    )
    return QualityScore(
        score=round(max(0.0, min(1.0, score)), 4),
        breakdown={
            "field_confidence": round(field_confidence, 4),
            "missing_core_sections": float(missing),
            "unverified_share": round(unverified_share, 4),
        },
    )


def _status(resume: ParsedResume, *, llm_ok: bool) -> Literal["ok", "partial", "failed"]:
    p = resume.personal
    usable = any((p.name, p.email, p.phone, resume.experience, resume.skills, resume.summary))
    if not usable:
        return "failed"
    return "ok" if llm_ok else "partial"


def _ms(since: float) -> int:
    return int((time.perf_counter() - since) * 1000)
