"""MatchResult and JobRequirements schemas (Step 4.1, plan §6.3)."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class RawJobRequirement(BaseModel):
    name: str
    required: bool = True
    importance: int = Field(default=3, ge=1, le=5)
    min_years: float | None = None


class RawJobExtraction(BaseModel):
    title: str = ""
    company: str | None = None
    seniority: str | None = None
    role_family: str | None = None
    min_total_experience_years: float | None = None
    education: list[str] = Field(default_factory=list)
    requirements: list[RawJobRequirement] = Field(default_factory=list)


class JobRequirement(BaseModel):
    skill_slug: str
    name: str
    required: bool = True
    importance: int = Field(default=3, ge=1, le=5)
    min_years: float | None = None


class JobRequirements(BaseModel):
    schema_version: str = "1.0"
    job_id: str | None = None
    title: str = ""
    company: str | None = None
    seniority: str | None = None
    role_family: str | None = None
    min_total_experience_years: float | None = None
    education: list[str] = Field(default_factory=list)
    requirements: list[JobRequirement] = Field(default_factory=list)
    raw_text_length: int = 0
    meta: dict[str, Any] = Field(default_factory=dict)


MatchType = Literal["exact", "descendant", "ancestor_or_sibling", "embedding", "missing"]


class RequirementCredit(BaseModel):
    requirement_slug: str
    requirement_name: str
    required: bool
    importance: int
    weight: float
    matched_slug: str | None = None
    matched_name: str | None = None
    match_type: MatchType = "missing"
    similarity: float = 0.0
    depth: float = 0.0
    credit: float = 0.0
    contribution: float = 0.0


class GapItem(BaseModel):
    skill_slug: str
    skill_name: str
    required: bool
    importance: int
    required_proficiency: str | None = None
    current_proficiency: str | None = None
    upskilling_hints: list[str] = Field(default_factory=list)


class MatchResult(BaseModel):
    schema_version: str = "1.0"
    job_id: str | None = None
    candidate_id: str | None = None
    score: float = Field(ge=0.0, le=1.0)
    is_match: bool
    threshold: float = Field(ge=0.0, le=1.0)
    preset: str | None = None
    components: dict[str, float] = Field(default_factory=dict)
    breakdown: list[RequirementCredit] = Field(default_factory=list)
    gaps: list[GapItem] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)
