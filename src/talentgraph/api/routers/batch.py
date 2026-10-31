"""Step 5.5: POST /api/v1/parse/batch (plan §8)."""

from uuid import UUID, uuid4

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Request,
    Response,
    UploadFile,
    status,
)

from talentgraph.agents.normalization.agent import NormalizationAgent
from talentgraph.agents.parsing.agent import ParsingAgent
from talentgraph.api.auth import require_api_key
from talentgraph.api.deps import (
    get_current_settings,
    get_normalization_agent,
    get_parsing_agent,
)
from talentgraph.api.ratelimit import limiter
from talentgraph.api.schemas import BatchUploadResponse
from talentgraph.config import Settings
from talentgraph.core.errors import FileTooLarge, UnsupportedContent
from talentgraph.orchestrator.batch import create_batch_record, process_batch_job

router = APIRouter(tags=["batch"])


@router.post(
    "/parse/batch",
    response_model=BatchUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload and process multiple resumes in the background",
    dependencies=[Depends(require_api_key)],
)
@limiter.limit("10/minute")
async def parse_batch(
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    settings: Settings = Depends(get_current_settings),
    parser: ParsingAgent = Depends(get_parsing_agent),
    normalizer: NormalizationAgent = Depends(get_normalization_agent),
) -> BatchUploadResponse:
    """Upload up to 20 resumes for background processing with bounded concurrency (plan §8)."""
    if not files:
        raise UnsupportedContent("No files provided in batch upload")

    if len(files) > settings.max_batch_files:
        raise FileTooLarge(
            f"Batch size {len(files)} exceeds maximum limit of {settings.max_batch_files} files"
        )

    # Read uploaded bytes into memory
    files_data: list[tuple[UUID, str, bytes]] = []
    filenames: list[str] = []
    for f in files:
        fname = f.filename or "resume.pdf"
        data = await f.read()
        item_id = uuid4()
        files_data.append((item_id, fname, data))
        filenames.append(fname)

    # Create batch record
    batch_job_id, _ = await create_batch_record(filenames)

    # Schedule background worker
    background_tasks.add_task(
        process_batch_job,
        batch_job_id,
        files_data,
        parser=parser,
        normalizer=normalizer,
        concurrency=settings.llm_max_concurrency,
    )

    return BatchUploadResponse(
        batch_job_id=str(batch_job_id),
        status="queued",
        total=len(files),
    )
