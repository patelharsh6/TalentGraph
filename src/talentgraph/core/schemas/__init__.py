"""Single source of truth for every cross-component contract (plan §5, §12)."""

from talentgraph.core.schemas.matching import MatchResult
from talentgraph.core.schemas.messages import (
    AgentError,
    AgentMessage,
    AgentName,
    AgentResult,
    QualityScore,
)
from talentgraph.core.schemas.resume import ParsedResume
from talentgraph.core.schemas.skills import SkillProfile

__all__ = [
    "AgentError",
    "AgentMessage",
    "AgentName",
    "AgentResult",
    "MatchResult",
    "ParsedResume",
    "QualityScore",
    "SkillProfile",
]
