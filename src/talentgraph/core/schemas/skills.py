"""SkillProfile schema (Step 3.1, plan §6.2).

Defines the output of the Normalization Agent: canonical skills with proficiency,
inferred skills via hierarchy/implication rules, and unrecognized skill strings.
"""

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class NormalizedSkill(BaseModel):
    """A canonical skill extracted and normalized from a resume or job description."""

    slug: str = Field(description="Unique canonical taxonomy slug (e.g. 'kubernetes', 'python')")
    name: str = Field(description="Display name of the skill (e.g. 'Kubernetes', 'Python')")
    category: str | None = Field(default=None, description="Taxonomy category name or slug")
    subcategory: str | None = Field(default=None, description="Taxonomy subcategory name or slug")
    domain: str | None = Field(default=None, description="Taxonomy root domain name or slug")
    level: int = Field(default=3, ge=0, le=3, description="Taxonomy depth: 0=domain .. 3=skill")

    proficiency: int = Field(default=2, ge=1, le=5, description="Proficiency level 1-5")
    years: float = Field(default=0.0, ge=0.0, description="Estimated years of experience")
    explanation: str = Field(
        default="", description="One-line explanation of the proficiency calculation"
    )

    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence in normalization")
    inferred: bool = Field(
        default=False, description="True if inferred via hierarchy/implication rules"
    )
    raw: list[str] = Field(
        default_factory=list, description="Original raw surface form(s) matched to this skill"
    )
    evidence: list[str] = Field(
        default_factory=list, description="Evidence snippets or roles supporting this skill"
    )
    method: Literal["exact", "fuzzy", "embedding", "llm", "inferred", "fallback"] = Field(
        default="exact", description="Cascade step that accepted this skill"
    )


class EmergingSkillMention(BaseModel):
    """An unrecognized skill candidate with context."""

    raw: str = Field(description="Original surface form of the unrecognized term")
    normalized: str = Field(description="Cleaned normalized representation")
    context: str | None = Field(default=None, description="Sentence or bullet context where found")


class SkillProfile(BaseModel):
    """Complete skill profile produced by the Normalization Agent."""

    schema_version: str = "2.0"
    candidate_id: UUID | None = None
    status: Literal["ok", "partial", "error"] = "ok"
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Overall profile confidence")

    skills: list[NormalizedSkill] = Field(
        default_factory=list, description="Canonical normalized skills (both direct and inferred)"
    )
    unrecognized: list[EmergingSkillMention] = Field(
        default_factory=list, description="Unrecognized skill candidates for emerging_skills store"
    )
    pipeline_version: str = "1.0"
    timings_ms: dict[str, int] = Field(default_factory=dict)
    meta: dict[str, Any] = Field(default_factory=dict)

    @property
    def direct_skills(self) -> list[NormalizedSkill]:
        """Skills directly matched from evidence (not inferred)."""
        return [s for s in self.skills if not s.inferred]

    @property
    def inferred_skills(self) -> list[NormalizedSkill]:
        """Skills inferred via implication rules or taxonomy hierarchy."""
        return [s for s in self.skills if s.inferred]

    def get(self, slug: str) -> NormalizedSkill | None:
        """Find a skill by canonical slug."""
        for s in self.skills:
            if s.slug == slug:
                return s
        return None
