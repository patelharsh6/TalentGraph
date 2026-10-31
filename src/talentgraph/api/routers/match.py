"""Step 5.4: POST /api/v1/match and /match/rank (plan §8)."""

import time
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
import structlog

from talentgraph import PIPELINE_VERSION
from talentgraph.agents.matching.agent import MatchingAgent
from talentgraph.agents.matching.blind import redact_skill_profile
from talentgraph.agents.matching.job_parser import JobParser
from talentgraph.api.auth import require_api_key
from talentgraph.api.deps import get_job_parser, get_matching_agent
from talentgraph.api.ratelimit import limiter
from talentgraph.api.schemas import (
    ApiResponse,
    MatchRequest,
    RankRequest,
    RankResponseData,
    ResponseMeta,
)
from talentgraph.core.errors import NotFound, TalentGraphError
from talentgraph.core.schemas.matching import JobRequirements, MatchResult
from talentgraph.core.schemas.skills import NormalizedSkill, SkillProfile
from talentgraph.db.in_memory import (
    InMemoryJobRecord,
    InMemoryMatchRecord,
    get_all_candidates_in_memory,
    get_candidate_in_memory,
    get_job_in_memory,
    save_job_in_memory,
    save_match_in_memory,
)
from talentgraph.db.models import Candidate, CandidateSkill, Job, Match, Skill
from talentgraph.db.session import async_session_scope

router = APIRouter(tags=["match"])
log = structlog.get_logger(__name__)


async def _resolve_candidate_profile(candidate_id: UUID) -> SkillProfile:
    """Fetch candidate profile from memory or DB."""
    # 1. Try memory
    mem = get_candidate_in_memory(candidate_id)
    if mem is not None:
        return mem.profile

    # 2. Try DB
    try:
        async with async_session_scope() as session:
            cand_res = await session.execute(select(Candidate).where(Candidate.id == candidate_id))
            if cand_res.scalar_one_or_none() is None:
                raise NotFound(f"Candidate {candidate_id} not found")

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
                        canonical_slug=sk.slug,
                        name=sk.name,
                        type=sk.type,  # type: ignore[arg-type]
                        proficiency=c_skill.proficiency,  # type: ignore[arg-type]
                        years=c_skill.years,
                        inferred=c_skill.inferred,
                        confidence=c_skill.confidence,
                        evidence=c_skill.evidence or [],
                    )
                )
            return SkillProfile(
                skills=skills,
                unrecognized_skills=[],
                meta={"candidate_id": str(candidate_id)},
            )
    except NotFound:
        raise
    except Exception as exc:
        log.debug("match.resolve_profile_db_failed", error=str(exc))

    raise NotFound(f"Candidate {candidate_id} not found")


async def _resolve_job_requirements(
    body: MatchRequest | RankRequest,
    job_parser: JobParser,
) -> tuple[UUID, JobRequirements]:
    """Parse or load JobRequirements from request body."""
    if body.job_id is not None:
        # Load existing job
        job_mem = get_job_in_memory(body.job_id)
        if job_mem is not None:
            return job_mem.id, job_mem.requirements

        try:
            async with async_session_scope() as session:
                res = await session.execute(select(Job).where(Job.id == body.job_id))
                db_job = res.scalar_one_or_none()
                if db_job is not None:
                    return db_job.id, JobRequirements.model_validate(db_job.requirements)
        except Exception:
            pass

        raise NotFound(f"Job {body.job_id} not found")

    if body.job is not None:
        # Parse new job
        raw_text = f"{body.job.title}\n\n{body.job.description}"
        reqs = await job_parser.parse(raw_text, title=body.job.title)
        job_id = uuid4()

        # Save in memory and DB
        save_job_in_memory(
            InMemoryJobRecord(
                job_id=job_id,
                title=body.job.title,
                raw_text=raw_text,
                requirements=reqs,
                text_sha256="",
            )
        )
        try:
            async with async_session_scope() as session:
                db_job = Job(
                    id=job_id,
                    title=body.job.title,
                    raw_text=raw_text,
                    requirements=reqs.model_dump(),
                    text_sha256="",
                )
                session.add(db_job)
        except Exception:
            pass

        return job_id, reqs

    raise TalentGraphError("Either 'job' or 'job_id' must be provided")


@router.post(
    "/match",
    response_model=ApiResponse[MatchResult],
    summary="Match a candidate against a job",
    dependencies=[Depends(require_api_key)],
)
@limiter.limit("30/minute")
async def match_candidate(
    request: Request,
    body: MatchRequest,
    blind: bool = Query(False, description="Run in blind screening mode"),
    include: str | None = Query(None, description="Set to 'trace' to include execution timeline"),
    matcher: MatchingAgent = Depends(get_matching_agent),
    job_parser: JobParser = Depends(get_job_parser),
) -> ApiResponse[MatchResult]:
    """Score candidate SkillProfile against JobRequirements with explainable breakdown."""
    t0 = time.perf_counter()

    profile = await _resolve_candidate_profile(body.candidate_id)
    job_id, job_reqs = await _resolve_job_requirements(body, job_parser)

    if blind:
        profile = redact_skill_profile(profile)

    thresh = body.threshold if body.threshold is not None else body.preset
    result = await matcher.match(profile, job_reqs, threshold=thresh)

    # Persist match record
    match_id = uuid4()
    save_match_in_memory(
        InMemoryMatchRecord(
            match_id=match_id,
            candidate_id=body.candidate_id,
            job_id=job_id,
            result=result,
            blind=blind,
        )
    )

    try:
        async with async_session_scope() as session:
            match_row = Match(
                id=match_id,
                candidate_id=body.candidate_id,
                job_id=job_id,
                score=result.score,
                threshold=result.threshold,
                is_match=result.is_match,
                blind=blind,
                breakdown=[b.model_dump() for b in result.breakdown],
                gaps=[g.model_dump() for g in result.gaps],
            )
            session.add(match_row)
    except Exception as exc:
        log.debug("match.db_persist_skipped", error=str(exc))

    total_latency = int((time.perf_counter() - t0) * 1000)

    meta = ResponseMeta(
        status="ok",
        trace_id=str(uuid4()),
        pipeline_version=PIPELINE_VERSION,
        latency_ms=total_latency,
        quality=1.0,
    )

    return ApiResponse(data=result, meta=meta)


@router.post(
    "/match/rank",
    response_model=list[RankResponseData],
    summary="Rank candidates against a job",
    dependencies=[Depends(require_api_key)],
)
@limiter.limit("20/minute")
async def rank_candidates(
    request: Request,
    body: RankRequest,
    blind: bool = Query(False, description="Run in blind screening mode"),
    matcher: MatchingAgent = Depends(get_matching_agent),
    job_parser: JobParser = Depends(get_job_parser),
) -> list[RankResponseData]:
    """Rank multiple candidates against a job description in descending score order."""
    _, job_reqs = await _resolve_job_requirements(body, job_parser)

    # Determine candidate IDs to rank
    cand_ids: list[UUID] = []
    if body.candidate_ids:
        cand_ids = body.candidate_ids
    else:
        # All candidates in memory
        mem_cands = get_all_candidates_in_memory()
        cand_ids = [c.id for c in mem_cands]
        # Also query DB candidates if available
        try:
            async with async_session_scope() as session:
                res = await session.execute(select(Candidate.id))
                db_ids = [r[0] for r in res.all()]
                for cid in db_ids:
                    if cid not in cand_ids:
                        cand_ids.append(cid)
        except Exception:
            pass

    ranked_items: list[RankResponseData] = []
    thresh = body.threshold if body.threshold is not None else body.preset

    for cid in cand_ids[: body.limit]:
        try:
            profile = await _resolve_candidate_profile(cid)
            if blind:
                profile = redact_skill_profile(profile)
            match_res = await matcher.match(profile, job_reqs, threshold=thresh)
            ranked_items.append(RankResponseData(candidate_id=str(cid), match=match_res))
        except Exception as exc:
            log.debug("match.rank_candidate_skipped", cid=str(cid), error=str(exc))

    ranked_items.sort(
        key=lambda item: (item.match.score, item.match.components.get("skill_score", 0.0)),
        reverse=True,
    )

    return ranked_items
