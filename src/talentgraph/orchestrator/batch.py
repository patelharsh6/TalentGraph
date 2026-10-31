"""Step 5.5: batch job processing, BackgroundTasks execution, stale-item recovery (plan §8)."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import select, update
import structlog

from talentgraph import PIPELINE_VERSION
from talentgraph.agents.normalization.agent import NormalizationAgent
from talentgraph.agents.parsing.agent import ParsingAgent
from talentgraph.core.ids import sha256_hex
from talentgraph.db.models import BatchJob, BatchItem, Candidate, CandidateSkill, Skill
from talentgraph.db.session import async_session_scope
from talentgraph.orchestrator.graph import run_parse_pipeline
from talentgraph.orchestrator.state import PipelineState

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

log = structlog.get_logger(__name__)

# In-memory store for test and offline fallback when DB is not running
_IN_MEMORY_JOBS: dict[UUID, dict[str, Any]] = {}
_IN_MEMORY_ITEMS: dict[UUID, list[dict[str, Any]]] = {}


def get_in_memory_batch(batch_job_id: UUID) -> dict[str, Any] | None:
    """Retrieve an in-memory batch record if present."""
    job = _IN_MEMORY_JOBS.get(batch_job_id)
    if not job:
        return None
    items = _IN_MEMORY_ITEMS.get(batch_job_id, [])
    res = dict(job)
    res["items"] = items
    return res


async def create_batch_record(
    filenames: list[str],
    session: AsyncSession | None = None,
) -> tuple[UUID, dict[str, Any]]:
    """Create a new BatchJob and its associated BatchItem records."""
    job_id = uuid4()
    now = datetime.now(UTC)
    total = len(filenames)

    item_records: list[dict[str, Any]] = []
    for fname in filenames:
        item_records.append(
            {
                "id": uuid4(),
                "batch_job_id": job_id,
                "filename": fname,
                "status": "queued",
                "candidate_id": None,
                "error": None,
            }
        )

    # In-memory record
    _IN_MEMORY_JOBS[job_id] = {
        "id": job_id,
        "status": "queued",
        "total": total,
        "succeeded": 0,
        "failed": 0,
        "partial": 0,
        "created_at": now,
        "finished_at": None,
    }
    _IN_MEMORY_ITEMS[job_id] = [dict(it) for it in item_records]

    if session is not None:
        try:
            job = BatchJob(
                id=job_id,
                status="queued",
                total=total,
                succeeded=0,
                failed=0,
                partial=0,
                created_at=now,
            )
            session.add(job)
            for it in item_records:
                b_item = BatchItem(
                    id=it["id"],
                    batch_job_id=job_id,
                    filename=it["filename"],
                    status="queued",
                )
                session.add(b_item)
            await session.commit()
        except Exception as exc:
            log.warning("batch.db_create_failed_fallback_in_memory", error=str(exc))

    return job_id, _IN_MEMORY_JOBS[job_id]


async def recover_stale_batches(engine: AsyncEngine | None = None) -> int:
    """Mark running or orphaned batch jobs and items as failed upon server startup (Step 5.5)."""
    # 1. Recover in-memory records
    recovered = 0
    for job in _IN_MEMORY_JOBS.values():
        if job["status"] == "running":
            job["status"] = "failed"
            job["finished_at"] = datetime.now(UTC)
            recovered += 1

    for items in _IN_MEMORY_ITEMS.values():
        for it in items:
            if it["status"] in ("running", "queued"):
                it["status"] = "failed"
                it["error"] = {
                    "code": "server_restart",
                    "detail": "Terminated by server restart",
                }
                recovered += 1

    # 2. Recover database records if database is configured
    try:
        async with async_session_scope() as session:
            stmt_items = (
                update(BatchItem)
                .where(BatchItem.status.in_(["running", "queued"]))
                .values(
                    status="failed",
                    error={
                        "code": "server_restart",
                        "detail": "Terminated by server restart",
                    },
                )
            )
            res_items = await session.execute(stmt_items)

            stmt_jobs = (
                update(BatchJob)
                .where(BatchJob.status == "running")
                .values(
                    status="failed",
                    finished_at=datetime.now(UTC),
                )
            )
            res_jobs = await session.execute(stmt_jobs)
            db_recovered = (res_items.rowcount or 0) + (res_jobs.rowcount or 0)
            if db_recovered > 0:
                log.info("batch.recovered_stale_db", count=db_recovered)
            recovered += db_recovered
    except Exception as exc:
        log.debug("batch.recovery_skipped_no_db", reason=str(exc))

    return recovered


async def process_batch_job(
    batch_job_id: UUID,
    files_data: list[tuple[UUID, str, bytes]],
    *,
    parser: ParsingAgent | None = None,
    normalizer: NormalizationAgent | None = None,
    concurrency: int = 4,
) -> None:
    """Background task processing a batch of resumes with bounded concurrency (Step 5.5)."""
    p_agent = parser or ParsingAgent()
    n_agent = normalizer or NormalizationAgent()
    semaphore = asyncio.Semaphore(concurrency)

    # Mark batch job as running
    if batch_job_id in _IN_MEMORY_JOBS:
        _IN_MEMORY_JOBS[batch_job_id]["status"] = "running"

    try:
        async with async_session_scope() as session:
            await session.execute(
                update(BatchJob).where(BatchJob.id == batch_job_id).values(status="running")
            )
    except Exception:
        pass

    async def _process_item(item_id: UUID, filename: str, file_bytes: bytes) -> None:
        async with semaphore:
            # Update item status to running
            if batch_job_id in _IN_MEMORY_ITEMS:
                for it in _IN_MEMORY_ITEMS[batch_job_id]:
                    if it["id"] == item_id:
                        it["status"] = "running"
                        break

            try:
                # Run parse pipeline
                input_state = PipelineState.from_bytes(file_bytes, filename=filename)
                result_state = await run_parse_pipeline(
                    input_state, parser=p_agent, normalizer=n_agent
                )

                if result_state.status == "failed" or not result_state.parsed_resume:
                    error_info = {
                        "code": "parse_failed",
                        "detail": (
                            result_state.errors[0].message
                            if result_state.errors
                            else "Parsing failed"
                        ),
                    }
                    _record_item_result(
                        batch_job_id, item_id, status="failed", error=error_info
                    )
                    return

                # Candidate ID from state or generated
                cand_id = uuid4()
                sha = sha256_hex(file_bytes)
                quality = (
                    result_state.parsed_resume.quality.score
                    if result_state.parsed_resume.quality
                    else None
                )

                # Persist to database if available
                try:
                    async with async_session_scope() as session:
                        candidate = Candidate(
                            id=cand_id,
                            file_sha256=sha,
                            parsed=result_state.parsed_resume.model_dump(),
                            quality=quality,
                            pipeline_version=PIPELINE_VERSION,
                        )
                        session.add(candidate)

                        # Persist CandidateSkills if profile exists
                        if result_state.skill_profile:
                            for sk in result_state.skill_profile.skills:
                                # Look up skill id if possible
                                skill_res = await session.execute(
                                    select(Skill.id).where(Skill.slug == sk.canonical_slug)
                                )
                                sk_id = skill_res.scalar_one_or_none()
                                if sk_id is not None:
                                    cand_skill = CandidateSkill(
                                        candidate_id=cand_id,
                                        skill_id=sk_id,
                                        proficiency=sk.proficiency,
                                        years=sk.years,
                                        inferred=sk.inferred,
                                        confidence=sk.confidence,
                                        evidence=sk.evidence,
                                    )
                                    session.add(cand_skill)
                except Exception as exc:
                    log.debug("batch.persist_candidate_skipped", error=str(exc))

                status = "partial" if result_state.status == "partial" else "succeeded"
                _record_item_result(
                    batch_job_id, item_id, status=status, candidate_id=cand_id
                )

            except Exception as exc:
                err = {
                    "code": getattr(exc, "code", "error"),
                    "detail": getattr(exc, "detail", str(exc)),
                }
                _record_item_result(
                    batch_job_id, item_id, status="failed", error=err
                )

    tasks = [_process_item(item_id, fname, b) for item_id, fname, b in files_data]
    await asyncio.gather(*tasks, return_exceptions=True)

    # Finalize batch job
    now = datetime.now(UTC)
    job_mem = _IN_MEMORY_JOBS.get(batch_job_id)
    if job_mem:
        failed_count = job_mem.get("failed", 0)
        job_mem["status"] = "completed_with_errors" if failed_count > 0 else "completed"
        job_mem["finished_at"] = now

    try:
        async with async_session_scope() as session:
            final_status = "completed_with_errors" if (job_mem and job_mem.get("failed", 0) > 0) else "completed"
            await session.execute(
                update(BatchJob)
                .where(BatchJob.id == batch_job_id)
                .values(
                    status=final_status,
                    succeeded=job_mem.get("succeeded", 0) if job_mem else 0,
                    failed=job_mem.get("failed", 0) if job_mem else 0,
                    partial=job_mem.get("partial", 0) if job_mem else 0,
                    finished_at=now,
                )
            )
    except Exception:
        pass


def _record_item_result(
    batch_job_id: UUID,
    item_id: UUID,
    *,
    status: str,
    candidate_id: UUID | None = None,
    error: dict[str, Any] | None = None,
) -> None:
    """Update in-memory and database status for a single batch item."""
    job_mem = _IN_MEMORY_JOBS.get(batch_job_id)
    if job_mem:
        if status == "succeeded":
            job_mem["succeeded"] = job_mem.get("succeeded", 0) + 1
        elif status == "partial":
            job_mem["partial"] = job_mem.get("partial", 0) + 1
        elif status == "failed":
            job_mem["failed"] = job_mem.get("failed", 0) + 1

    items_mem = _IN_MEMORY_ITEMS.get(batch_job_id, [])
    for it in items_mem:
        if it["id"] == item_id:
            it["status"] = status
            it["candidate_id"] = str(candidate_id) if candidate_id else None
            it["error"] = error
            break

    # Also update DB asynchronously if reachable
    async def _update_db() -> None:
        try:
            async with async_session_scope() as session:
                await session.execute(
                    update(BatchItem)
                    .where(BatchItem.id == item_id)
                    .values(
                        status=status,
                        candidate_id=candidate_id,
                        error=error,
                    )
                )
        except Exception:
            pass

    asyncio.create_task(_update_db())
