from uuid import uuid4

import pytest
from pydantic import ValidationError

from talentgraph.core.schemas import AgentMessage, AgentResult, QualityScore


def test_reply_keeps_trace_and_links_parent() -> None:
    task = AgentMessage(trace_id=uuid4(), sender="orchestrator", recipient="parser", type="task")
    result = task.reply(type="result", payload={"ok": True})
    assert result.trace_id == task.trace_id
    assert result.parent_id == task.message_id
    assert (result.sender, result.recipient) == ("parser", "orchestrator")


def test_message_round_trips_json() -> None:
    msg = AgentMessage(trace_id=uuid4(), sender="parser", recipient="normalizer", type="task")
    assert AgentMessage.model_validate_json(msg.model_dump_json()) == msg


def test_quality_score_bounds() -> None:
    with pytest.raises(ValidationError):
        QualityScore(score=1.5)
    AgentResult(status="ok", quality=QualityScore(score=0.9), latency_ms=12)
