"""Single source of truth for every cross-component contract (plan §5, §12)."""

from talentgraph.core.schemas.matching import (
    GapItem,
    JobRequirement,
    JobRequirements,
    MatchResult,
    RawJobExtraction,
    RawJobRequirement,
    RequirementCredit,
)
from talentgraph.core.schemas.messages import (
    AgentError,
    AgentMessage,
    AgentName,
    AgentResult,
    AgentRun,
    QualityScore,
)
from talentgraph.core.schemas.resume import ParsedResume, ParseResult, ResumeExtraction
from talentgraph.core.schemas.skills import EmergingSkillMention, NormalizedSkill, SkillProfile

__all__ = [
    "AgentError",
    "AgentMessage",
    "AgentName",
    "AgentResult",
    "AgentRun",
    "EmergingSkillMention",
    "GapItem",
    "JobRequirement",
    "JobRequirements",
    "MatchResult",
    "NormalizedSkill",
    "ParseResult",
    "ParsedResume",
    "QualityScore",
    "RawJobExtraction",
    "RawJobRequirement",
    "RequirementCredit",
    "ResumeExtraction",
    "SkillProfile",
]
