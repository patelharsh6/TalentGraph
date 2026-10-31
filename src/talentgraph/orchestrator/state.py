"""Step 4.6: PipelineState carried through the LangGraph graph (plan §4.2)."""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from talentgraph.core.schemas.matching import JobRequirements, MatchResult
from talentgraph.core.schemas.messages import AgentError, AgentRun
from talentgraph.core.schemas.resume import ParsedResume
from talentgraph.core.schemas.skills import SkillProfile

PipelineStatus = Literal["ok", "partial", "failed"]


class PipelineState(BaseModel):
    """Complete mutable state flowing through the resume parsing and matching graph."""

    trace_id: UUID = Field(default_factory=uuid4)
    batch_item_id: UUID | None = None
    candidate_id: UUID | None = None

    input_meta: dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata on input file: filename, mime, sha256, bytes_length",
    )
    file_bytes: bytes | None = Field(default=None, repr=False)

    raw_document: dict[str, Any] | None = None
    parsed_resume: ParsedResume | None = None
    raw_skills: list[str] = Field(
        default_factory=list,
        description="Raw skill strings retained when normalization degrades",
    )
    skill_profile: SkillProfile | None = None

    job: JobRequirements | str | None = None
    threshold: float | str | None = None
    match_result: MatchResult | None = None

    blind: bool = False

    agent_runs: list[AgentRun] = Field(default_factory=list)
    errors: list[AgentError] = Field(default_factory=list)
    status: PipelineStatus = "ok"

    def record_run(self, run: AgentRun) -> None:
        """Append an execution telemetry record."""
        self.agent_runs.append(run)

    def record_error(self, error: AgentError) -> None:
        """Append an agent error and degrade status if necessary."""
        self.errors.append(error)
        if self.status == "ok":
            self.status = "partial"
