"""MatchResult schema. Placeholder for Phase 0; finalized in Step 4.1 (plan §6.3)."""

from typing import Any

from pydantic import BaseModel, Field


class MatchResult(BaseModel):
    schema_version: str = "1.0"
    score: float = Field(ge=0.0, le=1.0)
    is_match: bool
    threshold: float = Field(ge=0.0, le=1.0)
    components: dict[str, float] = Field(default_factory=dict)
    breakdown: list[dict[str, Any]] = Field(default_factory=list)
    gaps: list[dict[str, Any]] = Field(default_factory=list)
