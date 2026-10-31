"""Shared agent message protocol and execution models (plan §5)."""

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

AgentName = Literal[
    "orchestrator",
    "parser",
    "verifier",
    "normalizer",
    "matcher",
    "search",
    "coach",
]
SCHEMA_VERSION = "1.0"


def _now() -> datetime:
    return datetime.now(UTC)


class QualityScore(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    breakdown: dict[str, float] = Field(default_factory=dict)


class AgentMessage(BaseModel):
    """Message envelope passed between components."""

    schema_version: str = SCHEMA_VERSION
    message_id: UUID = Field(default_factory=uuid4)
    trace_id: UUID
    parent_id: UUID | None = None
    sender: AgentName
    recipient: AgentName
    type: Literal["task", "result", "error", "heartbeat"]
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_now)
    attempt: int = 1

    def reply(
        self, *, type: Literal["result", "error"], payload: dict[str, Any]
    ) -> "AgentMessage":
        """Build the response envelope, keeping the trace and linking parent_id."""
        return AgentMessage(
            trace_id=self.trace_id,
            parent_id=self.message_id,
            sender=self.recipient,
            recipient=self.sender,
            type=type,
            payload=payload,
            attempt=self.attempt,
        )


class AgentResult(BaseModel):
    """Result returned by an agent inside LangGraph or via handle()."""

    status: Literal["ok", "partial", "failed"]
    data: dict[str, Any] | None = None
    quality: QualityScore
    latency_ms: int
    warnings: list[str] = Field(default_factory=list)


class AgentError(BaseModel):
    """Detailed error record during an agent attempt."""

    agent: AgentName
    code: str
    message: str
    retryable: bool
    attempt: int = 1


class AgentRun(BaseModel):
    """Execution telemetry record for an agent attempt."""

    trace_id: UUID
    agent: AgentName
    attempt: int = 1
    status: Literal["ok", "partial", "failed"]
    latency_ms: int
    quality: float | None = None
    error_code: str | None = None
    started_at: datetime = Field(default_factory=_now)
