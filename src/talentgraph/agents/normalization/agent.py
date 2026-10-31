"""Step 3.8: NormalizationAgent (ParsedResume to SkillProfile, plan §6.2).

Performs end-to-end skill normalization for a parsed resume:
1. Normalizes skills from resume.skills, experience, and projects via SkillCascade.
2. Ties role durations and bullet evidence to skills to estimate 1-5 proficiency and years.
3. Infers higher-level taxonomy ancestors and implication rules with `inferred: true`.
4. Records unrecognized terms into the emerging skills store.
5. Computes a normalization quality score and determines pipeline status ("ok" | "partial").
"""

from __future__ import annotations

import asyncio
import re
import time
from datetime import date, timedelta
from typing import Any, Literal, cast
from uuid import UUID

import structlog

from talentgraph import PIPELINE_VERSION
from talentgraph.agents.base import Agent
from talentgraph.agents.normalization.cascade import (
    CascadeResult,
    NormalizationConfig,
    SkillCascade,
)
from talentgraph.agents.normalization.emerging import EmergingSkillStore
from talentgraph.agents.normalization.hierarchy import infer_hierarchy
from talentgraph.agents.normalization.proficiency import (
    ProficiencyConfig,
    estimate_proficiency,
)
from talentgraph.config import Settings, get_settings
from talentgraph.core.schemas.messages import AgentMessage, AgentName, AgentResult, QualityScore
from talentgraph.core.schemas.resume import Experience, ParsedResume
from talentgraph.core.schemas.skills import (
    EmergingSkillMention,
    NormalizedSkill,
    SkillProfile,
)
from talentgraph.db.repositories.taxonomy import (
    TaxonomyRepository,
    get_taxonomy_repository,
)
from talentgraph.embeddings.skill_index import SkillIndex, get_skill_index
from talentgraph.llm.client import LLMClient, get_llm

log = structlog.get_logger(__name__)


def _parse_iso_date(val: str | None, default_day: int = 1) -> date | None:
    """Parse 'YYYY-MM' or 'YYYY' into a date object."""
    if not val:
        return None
    val = val.strip()
    try:
        parts = val.split("-")
        y = int(parts[0])
        m = int(parts[1]) if len(parts) > 1 else 1
        d = min(default_day, 28)
        return date(y, m, d)
    except (ValueError, IndexError):
        return None


def _extract_role_interval(exp: Experience, today: date) -> tuple[date, date] | None:
    """Extract (start, end) date interval for an experience role."""
    start_str = exp.start.value if exp.start and exp.start.value else None
    end_str = exp.end.value if exp.end and exp.end.value else None

    start_dt = _parse_iso_date(start_str, default_day=1)
    if not start_dt:
        if exp.duration_months and exp.duration_months > 0:
            end_dt = today
            start_dt = today - timedelta(days=int(exp.duration_months * 30.4375))
            return (start_dt, end_dt)
        return None

    if exp.is_current or not end_str:
        end_dt = today
    else:
        end_dt = _parse_iso_date(end_str, default_day=28) or today

    if start_dt > end_dt:
        return None
    return (start_dt, end_dt)


def profile_quality_score(profile: SkillProfile) -> QualityScore:
    """Compute overall normalization quality score."""
    direct = profile.direct_skills
    unrec = profile.unrecognized

    if not direct and not unrec:
        return QualityScore(score=0.0, breakdown={"direct_count": 0, "unrecognized_count": 0})

    total_mentions = len(direct) + len(unrec)
    recognition_rate = len(direct) / total_mentions if total_mentions > 0 else 0.0

    mean_conf = sum(s.confidence for s in direct) / len(direct) if direct else 0.0
    final_score = round(mean_conf * (0.5 + 0.5 * recognition_rate), 4)

    return QualityScore(
        score=max(0.0, min(1.0, final_score)),
        breakdown={
            "direct_count": float(len(direct)),
            "inferred_count": float(len(profile.inferred_skills)),
            "unrecognized_count": float(len(unrec)),
            "recognition_rate": round(recognition_rate, 4),
            "mean_confidence": round(mean_conf, 4),
        },
    )


class NormalizationAgent(Agent):
    """NormalizationAgent turning ParsedResume into SkillProfile (Step 3.8, plan §6.2)."""

    name: AgentName = "normalizer"

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        llm: LLMClient | None = None,
        repo: TaxonomyRepository | None = None,
        skill_index: SkillIndex | None = None,
        cascade: SkillCascade | None = None,
        emerging_store: EmergingSkillStore | None = None,
        config: NormalizationConfig | None = None,
        prof_config: ProficiencyConfig | None = None,
        today: date | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._llm = llm if llm is not None else get_llm(self._settings)
        self._repo = repo or get_taxonomy_repository()
        self._skill_index = skill_index or get_skill_index()
        self._config = config or NormalizationConfig.load()
        self._prof_config = prof_config or ProficiencyConfig.load()
        self._today = today or date.today()

        self.cascade = cascade or SkillCascade(
            repo=self._repo,
            skill_index=self._skill_index,
            llm=self._llm,
            config=self._config,
        )
        self.emerging_store = emerging_store or EmergingSkillStore(self._config)

    async def startup(self) -> None:
        """Agent startup hook."""
        pass

    async def shutdown(self) -> None:
        """Agent shutdown hook."""
        pass

    async def normalize_skill_string(
        self, raw: str, context: str | None = None
    ) -> list[CascadeResult]:
        """Normalize a raw skill string directly through the cascade."""
        return await self.cascade.normalize_one(raw, context=context)

    async def normalize(
        self,
        resume: ParsedResume,
        *,
        candidate_id: UUID | None = None,
    ) -> SkillProfile:
        """Normalize all skills in a ParsedResume to produce a validated SkillProfile."""
        start_time = time.perf_counter()
        timings: dict[str, int] = {}

        # -----------------------------------------------------------------------------------------
        # 1. Collect raw skill mentions and role contexts from resume
        # -----------------------------------------------------------------------------------------
        t0 = time.perf_counter()

        # Mentions: (raw_text, context_text, interval, evidence_snippet, is_skills_section)
        mentions: list[tuple[str, str | None, tuple[date, date] | None, str | None, bool]] = []

        # A. Skills section mentions
        for s in resume.skills:
            if s.raw and s.raw.strip():
                mentions.append((s.raw.strip(), s.evidence, None, s.evidence, True))

        # B. Experience roles
        role_data: list[tuple[tuple[date, date] | None, list[str], str]] = []
        for exp in resume.experience:
            interval = _extract_role_interval(exp, self._today)
            bullets = [r.value for r in exp.responsibilities if r and r.value]
            title = exp.title.value if exp.title and exp.title.value else ""
            company = exp.company.value if exp.company and exp.company.value else ""
            role_header = f"{title} at {company}".strip()
            role_ctx = f"{role_header}: " + " ".join(bullets) if bullets else role_header

            role_data.append((interval, bullets, role_ctx))

            for sk_raw in exp.skills_mentioned:
                if sk_raw and sk_raw.strip():
                    # Find matching bullet as evidence
                    best_bullet = next(
                        (b for b in bullets if sk_raw.lower() in b.lower()),
                        role_header,
                    )
                    mentions.append((sk_raw.strip(), role_ctx, interval, best_bullet, False))

        # C. Projects
        for proj in resume.projects:
            proj_title = proj.name.value if proj.name and proj.name.value else "Project"
            desc = proj.description.value if proj.description and proj.description.value else ""
            proj_ctx = f"{proj_title}: {desc}".strip()
            for tech in proj.technologies:
                if tech and tech.strip():
                    mentions.append((tech.strip(), proj_ctx, None, proj_ctx, False))

        timings["collect_mentions"] = int((time.perf_counter() - t0) * 1000)

        # -----------------------------------------------------------------------------------------
        # 2. Run cascade on each mention
        # -----------------------------------------------------------------------------------------
        t0 = time.perf_counter()

        # Accumulator per canonical slug:
        # {slug: {canonical, raw_forms, confidences, methods, intervals, evidence, is_skills_only}}
        skill_acc: dict[str, dict[str, Any]] = {}
        unrecognized_mentions: list[EmergingSkillMention] = []
        degraded = False

        for raw_str, ctx, interval, evidence_snip, is_skills_sec in mentions:
            cascade_results = await self.cascade.normalize_one(raw_str, context=ctx)
            for res in cascade_results:
                if res.method == "fallback":
                    degraded = True

                if res.canonical is not None:
                    slug = res.canonical.slug
                    if slug not in skill_acc:
                        skill_acc[slug] = {
                            "canonical": res.canonical,
                            "raw_forms": set(),
                            "confidences": [],
                            "methods": set(),
                            "intervals": [],
                            "evidence": [],
                            "is_skills_only": is_skills_sec,
                        }

                    entry = skill_acc[slug]
                    entry["raw_forms"].add(res.candidate_text)
                    entry["confidences"].append(res.confidence)
                    entry["methods"].add(res.method)
                    if interval:
                        entry["intervals"].append(interval)
                        entry["is_skills_only"] = False
                    if evidence_snip and evidence_snip not in entry["evidence"]:
                        entry["evidence"].append(evidence_snip)
                    if not is_skills_sec:
                        entry["is_skills_only"] = False
                elif res.unrecognized is not None:
                    unrecognized_mentions.append(res.unrecognized)
                    self.emerging_store.record_mention_sync(res.unrecognized)

        # For skills originally only in the skills section, check if their name or aliases appear
        # in experience roles or bullets so they are credited for experience duration
        for slug, entry in skill_acc.items():
            if entry["is_skills_only"]:
                canon_name = entry["canonical"].name.lower()
                slug_name = slug.replace("-", " ")
                for interval, bullets, role_ctx in role_data:
                    # check match in role context
                    pattern = rf"\b({re.escape(canon_name)}|{re.escape(slug_name)})\b"
                    if re.search(pattern, role_ctx, re.IGNORECASE):
                        if interval:
                            entry["intervals"].append(interval)
                            entry["is_skills_only"] = False
                        matching_bullet = next(
                            (b for b in bullets if re.search(pattern, b, re.IGNORECASE)),
                            None,
                        )
                        if matching_bullet and matching_bullet not in entry["evidence"]:
                            entry["evidence"].append(matching_bullet)
                            entry["is_skills_only"] = False

        timings["cascade"] = int((time.perf_counter() - t0) * 1000)

        # -----------------------------------------------------------------------------------------
        # 3. Build direct NormalizedSkill objects with proficiency
        # -----------------------------------------------------------------------------------------
        t0 = time.perf_counter()
        direct_skills: list[NormalizedSkill] = []

        method_priority = ["exact", "fuzzy", "embedding", "llm", "fallback"]

        for _slug, data in skill_acc.items():
            canon = data["canonical"]
            prof_res = estimate_proficiency(
                role_intervals=data["intervals"],
                evidence_texts=data["evidence"],
                is_skills_section_only=data["is_skills_only"],
                config=self._prof_config,
            )

            # Pick best method
            methods = data["methods"]
            chosen_method = next((m for m in method_priority if m in methods), "exact")

            # Ancestors for category and domain
            cat_name = None
            dom_name = None
            if canon.parent_slug:
                parent = self._repo.get_skill(canon.parent_slug)
                if parent:
                    cat_name = parent.name
            ancestors = self._repo.get_ancestors(canon.slug)
            if ancestors:
                dom_name = ancestors[-1].name

            direct_skill = NormalizedSkill(
                slug=canon.slug,
                name=canon.name,
                category=cat_name,
                domain=dom_name,
                level=canon.level,
                proficiency=prof_res.level,
                years=prof_res.years,
                explanation=prof_res.explanation,
                confidence=round(max(data["confidences"]) if data["confidences"] else 1.0, 3),
                inferred=False,
                raw=sorted(list(data["raw_forms"])),
                evidence=data["evidence"][:3],
                method=cast(
                    Literal["exact", "fuzzy", "embedding", "llm", "inferred", "fallback"],
                    chosen_method,
                ),
            )
            direct_skills.append(direct_skill)

        # Sort direct skills alphabetically by name
        direct_skills.sort(key=lambda s: s.name.lower())
        timings["proficiency"] = int((time.perf_counter() - t0) * 1000)

        # -----------------------------------------------------------------------------------------
        # 4. Infer hierarchy and implication rules
        # -----------------------------------------------------------------------------------------
        t0 = time.perf_counter()
        inferred_skills = infer_hierarchy(direct_skills, self._repo)
        inferred_skills.sort(key=lambda s: s.name.lower())
        timings["hierarchy"] = int((time.perf_counter() - t0) * 1000)

        all_skills = direct_skills + inferred_skills

        # -----------------------------------------------------------------------------------------
        # 5. Build final SkillProfile and quality score
        # -----------------------------------------------------------------------------------------
        status: Literal["ok", "partial", "error"] = "ok"
        if degraded or (not direct_skills and unrecognized_mentions):
            status = "partial"
        elif not all_skills:
            status = "error"

        timings["total"] = int((time.perf_counter() - start_time) * 1000)

        profile = SkillProfile(
            candidate_id=candidate_id,
            status=status,
            confidence=1.0,
            skills=all_skills,
            unrecognized=unrecognized_mentions,
            pipeline_version=PIPELINE_VERSION,
            timings_ms=timings,
            meta={
                "direct_skill_count": len(direct_skills),
                "inferred_skill_count": len(inferred_skills),
                "unrecognized_count": len(unrecognized_mentions),
                "degraded": degraded,
            },
        )

        quality = profile_quality_score(profile)
        profile.confidence = quality.score
        profile.meta["quality_breakdown"] = quality.breakdown

        return profile

    def normalize_sync(
        self,
        resume: ParsedResume,
        *,
        candidate_id: UUID | None = None,
    ) -> SkillProfile:
        """Synchronous wrapper for normalize."""
        return asyncio.run(self.normalize(resume, candidate_id=candidate_id))

    async def handle(self, msg: AgentMessage) -> AgentResult:
        """Handle incoming message per Agent protocol."""
        raw_resume = msg.payload.get("resume")
        if raw_resume is None:
            return AgentResult(
                status="failed",
                data={"error": "Missing 'resume' in payload"},
                quality=QualityScore(score=0.0),
                latency_ms=0,
            )

        if isinstance(raw_resume, ParsedResume):
            resume = raw_resume
        elif isinstance(raw_resume, dict):
            resume = ParsedResume.model_validate(raw_resume)
        else:
            return AgentResult(
                status="failed",
                data={"error": "Payload 'resume' is not a ParsedResume"},
                quality=QualityScore(score=0.0),
                latency_ms=0,
            )

        profile = await self.normalize(resume)
        agent_status: Literal["ok", "partial", "failed"] = (
            "failed" if profile.status == "error" else profile.status
        )

        return AgentResult(
            status=agent_status,
            data=profile.model_dump(mode="json"),
            quality=QualityScore(
                score=profile.confidence,
                breakdown=profile.meta.get("quality_breakdown", {}),
            ),
            latency_ms=profile.timings_ms.get("total", 0),
        )
