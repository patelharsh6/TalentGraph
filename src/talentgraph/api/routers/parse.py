"""Step 5.4: POST /api/v1/parse (plan §8)."""

import time
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile
from sqlalchemy import select
import structlog

from talentgraph import PIPELINE_VERSION
from talentgraph.agents.normalization.agent import NormalizationAgent
from talentgraph.agents.parsing.agent import ParsingAgent
from talentgraph.agents.parsing.detect import check_size, detect_file_type
from talentgraph.api.auth import require_api_key
from talentgraph.api.deps import (
    get_current_settings,
    get_normalization_agent,
    get_parsing_agent,
)
from talentgraph.api.ratelimit import limiter
from talentgraph.api.schemas import ApiResponse, ParseResponseData, ResponseMeta
from talentgraph.config import Settings
from talentgraph.core.errors import TalentGraphError, UnsupportedContent
from talentgraph.core.ids import sha256_hex
from talentgraph.db.in_memory import InMemoryCandidateRecord, save_candidate_in_memory
from talentgraph.db.models import Candidate, CandidateSkill, Skill
from talentgraph.db.session import async_session_scope
from talentgraph.orchestrator.graph import run_parse_pipeline
from talentgraph.orchestrator.state import PipelineState

router = APIRouter(tags=["parse"])
log = structlog.get_logger(__name__)


@router.post(
    "/parse",
    response_model=ApiResponse[ParseResponseData],
    summary="Upload and parse a single resume",
    dependencies=[Depends(require_api_key)],
)
@limiter.limit("20/minute")
async def parse_resume(
    request: Request,
    file: UploadFile = File(...),
    include: str | None = Query(None, description="Set to 'trace' to include execution timeline"),
    settings: Settings = Depends(get_current_settings),
    parser: ParsingAgent = Depends(get_parsing_agent),
    normalizer: NormalizationAgent = Depends(get_normalization_agent),
) -> ApiResponse[ParseResponseData]:
    """Upload one resume (PDF, DOCX, TXT) and return structured parsed data and normalized skills."""
    t0 = time.perf_counter()
    data = await file.read()

    # 1. Size and file type checks (plan §8.1)
    check_size(data, max_mb=settings.max_upload_mb)
    kind, _ = detect_file_type(data)

    # 2. Run LangGraph parse & normalize pipeline
    filename = file.filename or f"resume.{kind}"
    input_state = PipelineState.from_bytes(data, filename=filename)
    result_state = await run_parse_pipeline(input_state, parser=parser, normalizer=normalizer)

    if result_state.status == "failed" or result_state.parsed_resume is None:
        err_msg = (
            result_state.errors[0].message
            if result_state.errors
            else "Failed to parse resume content"
        )
        raise UnsupportedContent(err_msg)

    # 3. Create and persist candidate
    candidate_id = uuid4()
    sha = sha256_hex(data)
    quality = (
        result_state.parsed_resume.quality.score
        if result_state.parsed_resume.quality
        else None
    )

    # In-memory save for offline test availability
    if result_state.skill_profile:
        save_candidate_in_memory(
            InMemoryCandidateRecord(
                candidate_id=candidate_id,
                file_sha256=sha,
                parsed=result_state.parsed_resume,
                profile=result_state.skill_profile,
                quality=quality,
            )
        )

    # Database persist if DB is running
    try:
        async with async_session_scope() as session:
            cand = Candidate(
                id=candidate_id,
                file_sha256=sha,
                parsed=result_state.parsed_resume.model_dump(),
                quality=quality,
                pipeline_version=PIPELINE_VERSION,
            )
            session.add(cand)

            if result_state.skill_profile:
                for sk in result_state.skill_profile.skills:
                    skill_res = await session.execute(
                        select(Skill.id).where(Skill.slug == sk.canonical_slug)
                    )
                    sk_id = skill_res.scalar_one_or_none()
                    if sk_id is not None:
                        c_skill = CandidateSkill(
                            candidate_id=candidate_id,
                            skill_id=sk_id,
                            proficiency=sk.proficiency,
                            years=sk.years,
                            inferred=sk.inferred,
                            confidence=sk.confidence,
                            evidence=sk.evidence,
                        )
                        session.add(c_skill)
    except Exception as exc:
        log.debug("parse.db_persist_skipped", error=str(exc))

    total_latency = int((time.perf_counter() - t0) * 1000)

    # 4. Prepare response envelope
    trace_data = None
    if include == "trace":
        trace_data = [run.model_dump() for run in result_state.agent_runs]

    meta = ResponseMeta(
        status=result_state.status,
        trace_id=str(result_state.trace_id),
        pipeline_version=PIPELINE_VERSION,
        latency_ms=total_latency,
        quality=quality,
        warnings=result_state.warnings,
        trace=trace_data,
    )

    response_data = ParseResponseData(
        candidate_id=str(candidate_id),
        parsed=result_state.parsed_resume,
        profile=result_state.skill_profile,  # type: ignore[arg-type]
    )

    return ApiResponse(data=response_data, meta=meta)
