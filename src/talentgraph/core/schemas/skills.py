"""SkillProfile schema. Placeholder for Phase 0; finalized in Step 3.1 (plan §6.2)."""

from typing import Any

from pydantic import BaseModel, Field


class SkillProfile(BaseModel):
    schema_version: str = "1.0"
    skills: list[dict[str, Any]] = Field(default_factory=list)
    inferred: list[dict[str, Any]] = Field(default_factory=list)
    emerging: list[dict[str, Any]] = Field(default_factory=list)
