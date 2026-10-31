"""Step 6.6: POST /api/v1/search talent search router (feature F1, plan §6.4)."""

from __future__ import annotations

import time
from uuid import uuid4

import structlog
from fastapi import APIRouter, Depends, Request, Response

from talentgraph import PIPELINE_VERSION
from talentgraph.agents.search.agent import SearchAgent
from talentgraph.api.auth import require_api_key
from talentgraph.api.deps import get_search_agent
from talentgraph.api.ratelimit import limiter
from talentgraph.api.schemas import (
    ApiResponse,
    ResponseMeta,
    SearchRequest,
    SearchResponseData,
)

router = APIRouter(tags=["search"])
log = structlog.get_logger(__name__)


@router.post(
    "/search",
    response_model=ApiResponse[SearchResponseData],
    dependencies=[Depends(require_api_key)],
    summary="Natural language talent search",
    description="Retrieve ranked candidates matching a natural language query with citations.",
)
@limiter.limit("60/minute")
async def search_candidates(
    request: Request,
    response: Response,
    body: SearchRequest,
    search_agent: SearchAgent = Depends(get_search_agent),
) -> ApiResponse[SearchResponseData]:
    """Execute natural language search for candidates."""
    start = time.perf_counter()

    plan, hits, used_llm = await search_agent.search(
        query=body.query,
        limit=body.limit,
    )

    elapsed_ms = int((time.perf_counter() - start) * 1000)

    # Exit Criterion 6-C: With no LLM, /search returns 'partial' from keyword planner
    response_status = "ok" if used_llm else "partial"
    trace_id = getattr(request.state, "trace_id", None) or str(uuid4())

    return ApiResponse(
        data=SearchResponseData(
            plan=plan.model_dump(),
            total_candidates=len(hits),
            results=hits,
        ),
        meta=ResponseMeta(
            status=response_status,
            trace_id=trace_id,
            pipeline_version=PIPELINE_VERSION,
            latency_ms=elapsed_ms,
        ),
    )
