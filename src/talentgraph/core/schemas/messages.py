"""Shared agent message protocol (plan §5)."""

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

AgentName = Literal["orchestrator", "parser", "normalizer", "matcher"]
SCHEMA_VERSION = "1.0"


def _now() -> datetime:
    return datetime.now(UTC)


class QualityScore(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    breakdown: dict[str, float] = Field(default_factory=dict)


class AgentMessage(BaseModel):
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

    def reply(self, *, type: Literal["result", "error"], payload: dict[str, Any]) -> "AgentMessage":
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
    status: Literal["ok", "partial", "failed"]
    data: dict[str, Any] | None = None
    quality: QualityScore
    latency_ms: int
    warnings: list[str] = Field(default_factory=list)


class AgentError(BaseModel):
    agent: AgentName
    code: str
    message: str
    retryable: bool
    attempt: int = 1
