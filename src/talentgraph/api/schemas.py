"""Pydantic schemas for REST API requests and responses (plan §8)."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from talentgraph.core.schemas.matching import MatchResult
from talentgraph.core.schemas.resume import ParsedResume
from talentgraph.core.schemas.skills import SkillProfile


class ResponseMeta(BaseModel):
    """Metadata envelope returned with pipeline API responses."""

    status: Literal["ok", "partial", "failed"] = "ok"
    trace_id: str
    pipeline_version: str
    latency_ms: int
    quality: float | None = None
    warnings: list[str] = Field(default_factory=list)
    trace: list[dict[str, Any]] | None = None


class ApiResponse[T](BaseModel):
    """Standard API response envelope (plan §8.1)."""

    data: T
    meta: ResponseMeta


class ParseResponseData(BaseModel):
    """Data payload for POST /api/v1/parse."""

    candidate_id: str
    parsed: ParsedResume
    profile: SkillProfile


class JobInput(BaseModel):
    """Raw job description input for matching."""

    title: str = Field(..., min_length=1)
    description: str = Field(..., min_length=10)


class MatchRequest(BaseModel):
    """Request payload for POST /api/v1/match."""

    candidate_id: UUID
    job: JobInput | None = None
    job_id: UUID | None = None
    threshold: float | None = None
    preset: str | None = None


class RankRequest(BaseModel):
    """Request payload for POST /api/v1/match/rank."""

    candidate_ids: list[UUID] | None = None
    job: JobInput | None = None
    job_id: UUID | None = None
    threshold: float | None = None
    preset: str | None = None
    limit: int = Field(default=50, ge=1, le=500)


class RankResponseData(BaseModel):
    """Ranked match result item."""

    candidate_id: str
    match: MatchResult


class BatchUploadResponse(BaseModel):
    """Response payload for POST /api/v1/parse/batch (202 Accepted)."""

    batch_job_id: str
    status: str
    total: int


class BatchItemResponse(BaseModel):
    """Status of an individual item in a batch."""

    id: str
    filename: str
    status: str
    candidate_id: str | None = None
    error: dict[str, Any] | None = None


class BatchStatusResponse(BaseModel):
    """Response payload for GET /api/v1/jobs/{id}."""

    id: str
    status: str
    total: int
    succeeded: int
    failed: int
    partial: int
    created_at: datetime
    finished_at: datetime | None = None
    items: list[BatchItemResponse] = Field(default_factory=list)


class CandidateDetailResponse(BaseModel):
    """Response payload for GET /api/v1/candidates/{id}."""

    id: str
    file_sha256: str
    parsed: dict[str, Any]
    quality: float | None
    pipeline_version: str
    created_at: datetime


class SkillDetailResponse(BaseModel):
    """Response payload for GET /api/v1/skills/{id}."""

    id: int
    slug: str
    name: str
    type: str
    level: int
    description: str | None = None
    ancestors: list[dict[str, Any]] = Field(default_factory=list)
    children: list[dict[str, Any]] = Field(default_factory=list)
    aliases: list[str] = Field(default_factory=list)
    related: list[dict[str, Any]] = Field(default_factory=list)


class SkillSearchItem(BaseModel):
    """Search hit in GET /api/v1/skills/search."""

    slug: str
    name: str
    score: float
    match_type: str
    type: str


# --------------------------------------------------------------------------------------------------
# Milestone 6: Search & Coach Schemas (plan §6.4, §6.5)
# --------------------------------------------------------------------------------------------------


class SearchRequest(BaseModel):
    """Request payload for POST /api/v1/search."""

    query: str = Field(..., min_length=2, description="Natural language search query")
    limit: int = Field(10, ge=1, le=50, description="Maximum candidates to return")


class SearchHit(BaseModel):
    """Ranked candidate hit in talent search."""

    candidate_id: str
    score: float
    reasons: list[str] = Field(default_factory=list)
    citations: dict[str, list[str]] = Field(default_factory=dict)
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)


class SearchResponseData(BaseModel):
    """Data envelope for POST /api/v1/search."""

    plan: dict[str, Any]
    total_candidates: int
    results: list[SearchHit]


class CoachRequest(BaseModel):
    """Request payload for POST /api/v1/coach."""

    candidate_id: str = Field(..., description="Target candidate ID")
    job_id: str | None = Field(None, description="Target job ID (if previously saved)")
    job: JobInput | None = Field(None, description="Inline job description")


class LearningGoal(BaseModel):
    """Structured learning plan item for a skill gap."""

    skill_slug: str
    skill_name: str
    rationale: str
    prerequisites: list[str] = Field(default_factory=list)
    recommended_order: int


class InterviewQuestion(BaseModel):
    """Targeted interview question for requirement verification."""

    requirement_name: str
    question: str
    target_competency: str
    preparation_tip: str


class BulletRewrite(BaseModel):
    """Resume bullet rewrite grounded strictly in existing evidence."""

    original_evidence: str
    improved_bullet: str
    highlighted_skills: list[str] = Field(default_factory=list)
    rationale: str


class CoachReport(BaseModel):
    """Career coach comprehensive report (feature F3)."""

    candidate_id: str
    job_id: str | None = None
    learning_plan: list[LearningGoal] = Field(default_factory=list)
    interview_questions: list[InterviewQuestion] = Field(default_factory=list)
    bullet_rewrites: list[BulletRewrite] = Field(default_factory=list)
    removed_claims: list[str] = Field(default_factory=list)
    revisions_count: int = 0
