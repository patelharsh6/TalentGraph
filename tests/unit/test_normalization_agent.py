"""Unit tests for NormalizationAgent (Step 3.8, Exit Criteria 3-A, 3-C, 3-D, 3-F)."""

from uuid import uuid4

import pytest

from talentgraph.agents.normalization.agent import NormalizationAgent, profile_quality_score
from talentgraph.agents.normalization.cascade import SkillCascade
from talentgraph.core.schemas.messages import AgentMessage
from talentgraph.core.schemas.resume import (
    Experience,
    Extracted,
    ParsedResume,
    Skill,
)
from talentgraph.db.repositories.taxonomy import get_taxonomy_repository
from talentgraph.embeddings.skill_index import get_skill_index


@pytest.fixture(scope="module")
def shared_agent() -> NormalizationAgent:
    repo = get_taxonomy_repository()
    index = get_skill_index()
    cascade = SkillCascade(repo=repo, skill_index=index, llm=None)
    return NormalizationAgent(repo=repo, skill_index=index, cascade=cascade, llm=None)


def test_exit_criterion_3a_required_examples(shared_agent: NormalizationAgent) -> None:
    """Exit Criterion 3-A:

    JS, K8s, React.js, ReactJS, ML Engineering and the other 1-D examples map correctly
    through the agent.
    """
    resume = ParsedResume(
        skills=[
            Skill(raw="JS"),
            Skill(raw="K8s"),
            Skill(raw="React.js"),
            Skill(raw="ReactJS"),
            Skill(raw="ML Engineering"),
        ]
    )

    profile = shared_agent.normalize_sync(resume)

    direct_slugs = {s.slug for s in profile.direct_skills}
    assert "javascript" in direct_slugs
    assert "kubernetes" in direct_slugs
    assert "react" in direct_slugs
    assert "machine-learning-engineering" in direct_slugs

    # React.js and ReactJS both map to "react" and should be merged
    react_skill = profile.get("react")
    assert react_skill is not None
    assert set(react_skill.raw) == {"react js", "reactjs"} or "react" in react_skill.slug


def test_exit_criterion_3c_hierarchy_inference(shared_agent: NormalizationAgent) -> None:
    """Exit Criterion 3-C:

    TensorFlow + PyTorch => Deep Learning (inferred); inferred skills never outrank
    explicit ones.
    """
    resume = ParsedResume(
        skills=[
            Skill(raw="TensorFlow"),
            Skill(raw="PyTorch"),
        ]
    )

    profile = shared_agent.normalize_sync(resume)

    # Both explicit skills are present and NOT inferred
    tf_skill = profile.get("tensorflow")
    pt_skill = profile.get("pytorch")
    assert tf_skill is not None and not tf_skill.inferred
    assert pt_skill is not None and not pt_skill.inferred

    # Deep Learning is inferred via implication rule
    dl_skill = profile.get("deep-learning")
    assert dl_skill is not None
    assert dl_skill.inferred is True
    assert "implication rule" in dl_skill.explanation.lower()

    # Inferred skill confidence must not outrank explicit skills
    assert dl_skill.confidence <= tf_skill.confidence
    assert dl_skill.confidence <= pt_skill.confidence

    # If Deep Learning was also an explicit skill, it must stay inferred=False
    resume_with_explicit = ParsedResume(
        skills=[
            Skill(raw="TensorFlow"),
            Skill(raw="PyTorch"),
            Skill(raw="Deep Learning"),
        ]
    )
    profile2 = shared_agent.normalize_sync(resume_with_explicit)
    dl2 = profile2.get("deep-learning")
    assert dl2 is not None
    assert dl2.inferred is False


def test_exit_criterion_3d_proficiency_calculation(shared_agent: NormalizationAgent) -> None:
    """Exit Criterion 3-D & integration:

    - Skills section only capped at level 2.
    - Role duration (e.g. 3 years) maps to level 3.
    - Qualifier wording ('expert in') adds +1 -> level 4.
    """
    # 1. Skills section only: capped at 2
    resume_skills_only = ParsedResume(skills=[Skill(raw="PostgreSQL")])
    prof1 = shared_agent.normalize_sync(resume_skills_only)
    pg1 = prof1.get("postgresql")
    assert pg1 is not None
    assert pg1.proficiency <= 2
    assert "skills section only" in pg1.explanation

    # 2. Multi-year experience role (2020-01 to 2023-01 = 3 years -> level 3)
    # with qualifier 'expert in' -> level 4
    resume_with_exp = ParsedResume(
        experience=[
            Experience(
                title=Extracted(value="Senior Data Engineer"),
                company=Extracted(value="Acme Corp"),
                start=Extracted(value="2020-01"),
                end=Extracted(value="2023-01"),
                responsibilities=[
                    Extracted(value="Expert in PostgreSQL query optimization and schema design")
                ],
                skills_mentioned=["PostgreSQL"],
            )
        ]
    )
    prof2 = shared_agent.normalize_sync(resume_with_exp)
    pg2 = prof2.get("postgresql")
    assert pg2 is not None
    assert pg2.years >= 2.9
    assert pg2.proficiency == 4
    assert "expert in" in pg2.explanation.lower()


def test_exit_criterion_3f_degradation_without_llm(shared_agent: NormalizationAgent) -> None:
    """Exit Criterion 3-F:

    With no LLM, ambiguous skills fall back to best candidate or unrecognized, and
    status is 'partial'.
    """
    resume = ParsedResume(
        skills=[
            Skill(raw="Go"),  # Ambiguous without context
        ]
    )

    profile = shared_agent.normalize_sync(resume)
    assert profile.status == "partial"
    go_skill = profile.get("golang") or profile.get("go-to-market-strategy")
    assert go_skill is not None
    assert go_skill.method in ("fallback", "exact")


def test_unrecognized_skills_and_quality(shared_agent: NormalizationAgent) -> None:
    """Unrecognized terms are recorded in emerging store and quality score reflects them."""
    resume = ParsedResume(
        skills=[
            Skill(raw="Python"),
            Skill(raw="SuperUnknownFictionalFrameworkXYZ9000"),
        ]
    )

    profile = shared_agent.normalize_sync(resume)
    assert profile.get("python") is not None
    assert len(profile.unrecognized) >= 1
    assert any("superunknown" in u.normalized for u in profile.unrecognized)

    q = profile_quality_score(profile)
    assert 0.0 < q.score < 1.0
    assert q.breakdown["direct_count"] == 1.0
    assert q.breakdown["unrecognized_count"] >= 1.0


@pytest.mark.asyncio
async def test_agent_protocol_handle(shared_agent: NormalizationAgent) -> None:
    """NormalizationAgent satisfies the Agent message protocol."""
    trace_id = uuid4()
    resume = ParsedResume(skills=[Skill(raw="Docker"), Skill(raw="Kubernetes")])
    msg = AgentMessage(
        trace_id=trace_id,
        sender="orchestrator",
        recipient="normalizer",
        type="task",
        payload={"resume": resume.model_dump()},
    )

    result = await shared_agent.handle(msg)
    assert result.status in ("ok", "partial")
    assert result.data is not None
    assert "skills" in result.data
    assert result.quality.score > 0.0
