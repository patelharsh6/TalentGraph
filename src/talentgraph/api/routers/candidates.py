"""Step 5.4: GET /api/v1/candidates/{id} and /skills (plan §8)."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import structlog
from fastapi import APIRouter, Query
from sqlalchemy import select

from talentgraph.api.schemas import CandidateDetailResponse
from talentgraph.core.schemas.resume import ParsedResume
from talentgraph.core.errors import NotFound
from talentgraph.core.schemas.skills import NormalizedSkill, SkillProfile
from talentgraph.db.in_memory import (
    get_all_candidates_in_memory,
    get_candidate_in_memory,
)
from talentgraph.db.models import Candidate, CandidateSkill, Skill
from talentgraph.db.session import async_session_scope

router = APIRouter(tags=["candidates"])
log = structlog.get_logger(__name__)


def _extract_str(val: Any, default: str = "") -> str:
    """Extract plain string from ExtractedField or dict."""
    if val is None:
        return default
    if isinstance(val, dict):
        return str(val.get("value") or default)
    if hasattr(val, "value"):
        return str(getattr(val, "value") or default)
    return str(val)


@router.get(
    "/candidates",
    summary="List available candidates",
)
async def list_candidates() -> list[dict[str, Any]]:
    """List loaded candidate profiles from in-memory store or DB."""
    results: list[dict[str, Any]] = []

    # 1. Check in-memory store first
    mem_cands = get_all_candidates_in_memory()
    for mem in mem_cands:
        if isinstance(mem.parsed, ParsedResume):
            parsed_dict: dict[str, Any] = mem.parsed.model_dump()
        elif isinstance(mem.parsed, dict):
            parsed_dict = mem.parsed
        else:
            parsed_dict = {}
        personal = parsed_dict.get("personal", {})
        experiences = parsed_dict.get("experience", [])
        raw_title = experiences[0].get("title", "Candidate") if experiences else "Candidate"
        cand_title = _extract_str(raw_title, "Candidate")
        cand_name = _extract_str(personal.get("name"), "Candidate")
        cand_summary = _extract_str(parsed_dict.get("summary"), "")
        top_skills = (
            [s.name for s in mem.profile.skills[:6]] if mem.profile and mem.profile.skills else []
        )
        results.append(
            {
                "id": str(mem.id),
                "name": cand_name,
                "title": cand_title,
                "summary": cand_summary,
                "skills_count": len(mem.profile.skills)
                if mem.profile and mem.profile.skills
                else 0,
                "top_skills": top_skills,
                "quality": mem.quality,
            }
        )

    # 2. If memory was empty, check DB
    if not results:
        try:
            async with async_session_scope() as session:
                stmt = select(Candidate).limit(50)
                res = await session.execute(stmt)
                for cand in res.scalars().all():
                    parsed_dict = cand.parsed or {}
                    personal = parsed_dict.get("personal", {})
                    experiences = parsed_dict.get("experience", [])
                    raw_title = (
                        experiences[0].get("title", "Candidate") if experiences else "Candidate"
                    )
                    cand_title = _extract_str(raw_title, "Candidate")
                    cand_name = _extract_str(personal.get("name"), "Candidate")
                    cand_summary = _extract_str(parsed_dict.get("summary"), "")
                    results.append(
                        {
                            "id": str(cand.id),
                            "name": cand_name,
                            "title": cand_title,
                            "summary": cand_summary,
                            "skills_count": len(parsed_dict.get("skills", [])),
                            "top_skills": [
                                s.get("name")
                                for s in parsed_dict.get("skills", [])[:6]
                                if isinstance(s, dict)
                            ],
                            "quality": cand.quality,
                        }
                    )
        except Exception as exc:
            log.debug("candidates.list_db_failed", error=str(exc))

    return results


@router.get(
    "/candidates/{candidate_id}",
    response_model=CandidateDetailResponse,
    summary="Retrieve a parsed candidate by ID",
)
async def get_candidate(candidate_id: UUID) -> CandidateDetailResponse:
    """Retrieve candidate parsed details, quality score, and metadata."""
    # 1. Try DB first
    try:
        async with async_session_scope() as session:
            stmt = select(Candidate).where(Candidate.id == candidate_id)
            res = await session.execute(stmt)
            cand = res.scalar_one_or_none()
            if cand is not None:
                return CandidateDetailResponse(
                    id=str(cand.id),
                    file_sha256=cand.file_sha256,
                    parsed=cand.parsed,
                    quality=cand.quality,
                    pipeline_version=cand.pipeline_version,
                    created_at=cand.created_at,
                )
    except Exception as exc:
        log.debug("candidates.db_lookup_failed", error=str(exc))

    # 2. Try in-memory fallback
    mem = get_candidate_in_memory(candidate_id)
    if mem is not None:
        return CandidateDetailResponse(
            id=str(mem.id),
            file_sha256=mem.file_sha256,
            parsed=mem.parsed.model_dump(),
            quality=mem.quality,
            pipeline_version="0.1.0",
            created_at=datetime.now(UTC),
        )

    raise NotFound(f"Candidate {candidate_id} not found")


@router.get(
    "/candidates/{candidate_id}/skills",
    response_model=SkillProfile,
    summary="Retrieve candidate skill profile with filters",
)
async def get_candidate_skills(
    candidate_id: UUID,
    type: str | None = Query(None, description="Filter by skill type: technical, soft, domain"),
    min_proficiency: int | None = Query(None, ge=1, le=5, description="Filter by min proficiency"),
    include_inferred: bool = Query(True, description="Include implied/inferred skills"),
) -> SkillProfile:
    """Retrieve normalized skills for a candidate with optional filtering."""
    # 1. Check in-memory store
    mem = get_candidate_in_memory(candidate_id)
    raw_profile: SkillProfile | None = None
    if mem is not None:
        raw_profile = mem.profile

    # 2. If not found in memory, check DB
    if raw_profile is None:
        try:
            async with async_session_scope() as session:
                # Get candidate
                cand_res = await session.execute(
                    select(Candidate).where(Candidate.id == candidate_id)
                )
                if cand_res.scalar_one_or_none() is None:
                    raise NotFound(f"Candidate {candidate_id} not found")

                # Get candidate skills
                stmt = (
                    select(CandidateSkill, Skill)
                    .join(Skill, CandidateSkill.skill_id == Skill.id)
                    .where(CandidateSkill.candidate_id == candidate_id)
                )
                res = await session.execute(stmt)
                skills: list[NormalizedSkill] = []
                for c_skill, sk in res.all():
                    skills.append(
                        NormalizedSkill(
                            slug=sk.slug,
                            name=sk.name,
                            category=sk.type,
                            proficiency=c_skill.proficiency,
                            years=c_skill.years or 0.0,
                            inferred=c_skill.inferred,
                            confidence=c_skill.confidence,
                            evidence=c_skill.evidence or [],
                        )
                    )
                raw_profile = SkillProfile(
                    skills=skills,
                    unrecognized=[],
                    meta={"candidate_id": str(candidate_id)},
                )
        except NotFound:
            raise
        except Exception as exc:
            log.debug("candidates.db_skills_failed", error=str(exc))

    if raw_profile is None:
        raise NotFound(f"Candidate {candidate_id} not found")

    # 3. Apply filters
    filtered_skills = [
        sk
        for sk in raw_profile.skills
        if (type is None or (sk.category and sk.category.lower() == type.lower()))
        and (min_proficiency is None or sk.proficiency >= min_proficiency)
        and (include_inferred or not sk.inferred)
    ]

    return SkillProfile(
        skills=filtered_skills,
        unrecognized=raw_profile.unrecognized,
        meta=raw_profile.meta,
    )
