"""Step 6.6: POST /api/v1/coach Career Coach router (feature F3, plan §6.5)."""

from __future__ import annotations

import time
from uuid import UUID, uuid4

import structlog
from fastapi import APIRouter, Depends, Request, Response

from talentgraph import PIPELINE_VERSION
from talentgraph.agents.coach.agent import CoachAgent
from talentgraph.agents.matching.job_parser import JobParser
from talentgraph.api.auth import require_api_key
from talentgraph.api.deps import get_coach_agent, get_job_parser
from talentgraph.api.ratelimit import limiter
from talentgraph.api.schemas import ApiResponse, CoachReport, CoachRequest, ResponseMeta
from talentgraph.core.schemas.matching import JobRequirements
from talentgraph.db.in_memory import get_job_in_memory

router = APIRouter(tags=["coach"])
log = structlog.get_logger(__name__)


@router.post(
    "/coach",
    response_model=ApiResponse[CoachReport],
    dependencies=[Depends(require_api_key)],
    summary="Career Coach report",
    description="Generate personalized learning plan, interview prep, and factual resume rewrites.",
)
@limiter.limit("30/minute")
async def generate_coach_report(
    request: Request,
    response: Response,
    body: CoachRequest,
    coach_agent: CoachAgent = Depends(get_coach_agent),
    job_parser: JobParser = Depends(get_job_parser),
) -> ApiResponse[CoachReport]:
    """Generate career coach report for a candidate against a target job."""
    start = time.perf_counter()

    job_reqs: JobRequirements | None = None
    if body.job is not None:
        # Inline job provided
        job_reqs = await job_parser.parse(body.job.description)
    elif body.job_id:
        # Check in-memory store
        try:
            mem_job = get_job_in_memory(uuid4() if len(body.job_id) != 36 else UUID(body.job_id))
            if mem_job is not None:
                job_reqs = mem_job.requirements
        except Exception:
            pass

    report = await coach_agent.coach(
        candidate_id=body.candidate_id,
        job_id=body.job_id,
        job_reqs=job_reqs,
    )

    elapsed_ms = int((time.perf_counter() - start) * 1000)
    trace_id = getattr(request.state, "trace_id", None) or str(uuid4())

    return ApiResponse(
        data=report,
        meta=ResponseMeta(
            status="ok",
            trace_id=trace_id,
            pipeline_version=PIPELINE_VERSION,
            latency_ms=elapsed_ms,
        ),
    )
