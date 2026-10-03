"""ParsedResume schema. Placeholder for Phase 0; the full schema (plan §6.1) is written in Phase
2.1.
"""

from typing import Any

from pydantic import BaseModel, Field


class ParsedResume(BaseModel):
    schema_version: str = "1.0"
    personal: dict[str, Any] = Field(default_factory=dict)
    summary: str | None = None
    experience: list[dict[str, Any]] = Field(default_factory=list)
    education: list[dict[str, Any]] = Field(default_factory=list)
    skills: list[dict[str, Any]] = Field(default_factory=list)
    certifications: list[dict[str, Any]] = Field(default_factory=list)
    projects: list[dict[str, Any]] = Field(default_factory=list)
    publications: list[dict[str, Any]] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)
