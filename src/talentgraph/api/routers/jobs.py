"""Step 5.5: GET /api/v1/jobs/{id} (plan §8)."""

from uuid import UUID

from fastapi import APIRouter
from sqlalchemy import select
import structlog

from talentgraph.api.schemas import BatchItemResponse, BatchStatusResponse
from talentgraph.core.errors import NotFound
from talentgraph.db.models import BatchJob, BatchItem
from talentgraph.db.session import async_session_scope
from talentgraph.orchestrator.batch import get_in_memory_batch

router = APIRouter(tags=["jobs"])
log = structlog.get_logger(__name__)


@router.get(
    "/jobs/{batch_job_id}",
    response_model=BatchStatusResponse,
    summary="Get batch processing progress and per-item status",
)
async def get_batch_job_status(batch_job_id: UUID) -> BatchStatusResponse:
    """Retrieve status, counts, and per-file progress for a background batch job."""
    # 1. Try DB first
    try:
        async with async_session_scope() as session:
            job_res = await session.execute(select(BatchJob).where(BatchJob.id == batch_job_id))
            job = job_res.scalar_one_or_none()
            if job is not None:
                items_res = await session.execute(
                    select(BatchItem).where(BatchItem.batch_job_id == batch_job_id)
                )
                items = items_res.scalars().all()
                item_responses = [
                    BatchItemResponse(
                        id=str(it.id),
                        filename=it.filename,
                        status=it.status,
                        candidate_id=str(it.candidate_id) if it.candidate_id else None,
                        error=it.error,
                    )
                    for it in items
                ]
                return BatchStatusResponse(
                    id=str(job.id),
                    status=job.status,
                    total=job.total,
                    succeeded=job.succeeded,
                    failed=job.failed,
                    partial=job.partial,
                    created_at=job.created_at,
                    finished_at=job.finished_at,
                    items=item_responses,
                )
    except Exception as exc:
        log.debug("jobs.db_lookup_failed", error=str(exc))

    # 2. Try in-memory fallback
    mem = get_in_memory_batch(batch_job_id)
    if mem is not None:
        item_responses = [
            BatchItemResponse(
                id=str(it["id"]),
                filename=it["filename"],
                status=it["status"],
                candidate_id=str(it["candidate_id"]) if it.get("candidate_id") else None,
                error=it.get("error"),
            )
            for it in mem.get("items", [])
        ]
        return BatchStatusResponse(
            id=str(mem["id"]),
            status=mem["status"],
            total=mem["total"],
            succeeded=mem["succeeded"],
            failed=mem["failed"],
            partial=mem["partial"],
            created_at=mem["created_at"],
            finished_at=mem.get("finished_at"),
            items=item_responses,
        )

    raise NotFound(f"Batch job {batch_job_id} not found")
