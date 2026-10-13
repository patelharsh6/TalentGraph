"""ORM models for every table in plan §7.1."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    ARRAY,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    type_annotation_map = {dict[str, Any]: JSONB, list[Any]: JSONB}


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


def _created_at() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now())


# --- Taxonomy -------------------------------------------------------------------------------------


class Skill(Base):
    __tablename__ = "skills"
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    type: Mapped[str] = mapped_column(String(20))  # technical | soft | domain
    level: Mapped[int] = mapped_column(SmallInteger)  # 0=domain .. 3=skill
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("skills.id"), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    taxonomy_version: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = _created_at()


class SkillAlias(Base):
    __tablename__ = "skill_aliases"
    id: Mapped[int] = mapped_column(primary_key=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id", ondelete="CASCADE"), index=True)
    alias: Mapped[str] = mapped_column(String(200))
    alias_normalized: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    ambiguous: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[str] = mapped_column(String(20))  # esco | onet | curated | variant | llm


class SkillImplication(Base):
    __tablename__ = "skill_implications"
    id: Mapped[int] = mapped_column(primary_key=True)
    antecedent_ids: Mapped[list[int]] = mapped_column(ARRAY(Integer))
    consequent_id: Mapped[int] = mapped_column(ForeignKey("skills.id", ondelete="CASCADE"))
    min_count: Mapped[int] = mapped_column(SmallInteger, default=1)
    confidence: Mapped[float] = mapped_column(Float)


class SkillRelation(Base):
    __tablename__ = "skill_relations"
    skill_id: Mapped[int] = mapped_column(
        ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True
    )
    related_id: Mapped[int] = mapped_column(
        ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True
    )
    kind: Mapped[str] = mapped_column(String(20), primary_key=True)  # related | prerequisite
    weight: Mapped[float] = mapped_column(Float, default=1.0)


class EmergingSkill(Base):
    __tablename__ = "emerging_skills"
    id: Mapped[int] = mapped_column(primary_key=True)
    normalized_text: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    occurrences: Mapped[int] = mapped_column(Integer, default=1)
    example_contexts: Mapped[list[Any]] = mapped_column(default=list)


# --- Candidates, jobs, matches --------------------------------------------------------------------


class Candidate(Base):
    __tablename__ = "candidates"
    id: Mapped[uuid.UUID] = _uuid_pk()
    file_sha256: Mapped[str] = mapped_column(String(64), index=True)
    parsed: Mapped[dict[str, Any]] = mapped_column()
    quality: Mapped[float | None] = mapped_column(Float)
    pipeline_version: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = _created_at()


class CandidateSkill(Base):
    __tablename__ = "candidate_skills"
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), primary_key=True
    )
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id"), primary_key=True)
    proficiency: Mapped[int] = mapped_column(SmallInteger)
    years: Mapped[float | None] = mapped_column(Float)
    inferred: Mapped[bool] = mapped_column(Boolean, default=False)
    confidence: Mapped[float] = mapped_column(Float)
    evidence: Mapped[list[Any]] = mapped_column(default=list)


class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[uuid.UUID] = _uuid_pk()
    title: Mapped[str] = mapped_column(String(300))
    raw_text: Mapped[str] = mapped_column(Text)
    requirements: Mapped[dict[str, Any]] = mapped_column()
    text_sha256: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = _created_at()


class Match(Base):
    __tablename__ = "matches"
    id: Mapped[uuid.UUID] = _uuid_pk()
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), index=True
    )
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    score: Mapped[float] = mapped_column(Float)
    threshold: Mapped[float] = mapped_column(Float)
    is_match: Mapped[bool] = mapped_column(Boolean)
    breakdown: Mapped[list[Any]] = mapped_column()
    gaps: Mapped[list[Any]] = mapped_column()
    created_at: Mapped[datetime] = _created_at()


# --- Batch processing -----------------------------------------------------------------------------


class BatchJob(Base):
    __tablename__ = "batch_jobs"
    id: Mapped[uuid.UUID] = _uuid_pk()
    # queued | running | completed | completed_with_errors | failed
    status: Mapped[str] = mapped_column(String(30), default="queued")
    total: Mapped[int] = mapped_column(Integer)
    succeeded: Mapped[int] = mapped_column(Integer, default=0)
    failed: Mapped[int] = mapped_column(Integer, default=0)
    partial: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = _created_at()
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class BatchItem(Base):
    __tablename__ = "batch_items"
    id: Mapped[uuid.UUID] = _uuid_pk()
    batch_job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("batch_jobs.id", ondelete="CASCADE"), index=True
    )
    filename: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), default="queued")
    candidate_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("candidates.id"))
    error: Mapped[dict[str, Any] | None] = mapped_column()


# --- Observability --------------------------------------------------------------------------------


class AgentRunRecord(Base):
    __tablename__ = "agent_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    trace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    agent: Mapped[str] = mapped_column(String(20))
    attempt: Mapped[int] = mapped_column(SmallInteger)
    status: Mapped[str] = mapped_column(String(10))
    latency_ms: Mapped[int] = mapped_column(Integer)
    quality: Mapped[float | None] = mapped_column(Float)
    error_code: Mapped[str | None] = mapped_column(String(50))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
