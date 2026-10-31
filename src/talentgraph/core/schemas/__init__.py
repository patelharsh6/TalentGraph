"""Single source of truth for every cross-component contract (plan §5, §12)."""

from talentgraph.core.schemas.matching import MatchResult
from talentgraph.core.schemas.messages import (
    AgentError,
    AgentMessage,
    AgentName,
    AgentResult,
    QualityScore,
)
from talentgraph.core.schemas.resume import ParsedResume, ParseResult, ResumeExtraction
from talentgraph.core.schemas.skills import EmergingSkillMention, NormalizedSkill, SkillProfile

__all__ = [
    "AgentError",
    "AgentMessage",
    "AgentName",
    "AgentResult",
    "EmergingSkillMention",
    "MatchResult",
    "NormalizedSkill",
    "ParseResult",
    "ParsedResume",
    "QualityScore",
    "ResumeExtraction",
    "SkillProfile",
]
