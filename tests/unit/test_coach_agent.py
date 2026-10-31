"""Unit tests for CoachAgent, critic stages, and degradation (Milestone 6)."""

from __future__ import annotations

import pytest

from talentgraph.agents.coach.agent import CoachAgent
from talentgraph.agents.coach.critic import (
    deterministic_verify_bullet,
    deterministic_verify_learning_plan,
)
from talentgraph.api.schemas import BulletRewrite, CoachReport, LearningGoal
from talentgraph.core.errors import ServiceUnavailable
from talentgraph.db.repositories.taxonomy import get_taxonomy_repository


@pytest.fixture
def repo():
    return get_taxonomy_repository()


@pytest.fixture
def sample_profile():
    return {
        "summary": "Software engineer with experience in Python and AWS.",
        "skills": [
            {"canonical_slug": "python", "raw": "Python", "evidence": "Built Python services."},
            {
                "canonical_slug": "amazon-web-services",
                "raw": "AWS",
                "evidence": "Deployed on AWS EC2.",
            },
        ],
        "experience": [
            {
                "company": "Tech Corp",
                "title": "Backend Engineer",
                "responsibilities": ["Maintained Python web APIs and improved deployment scripts."],
            }
        ],
    }


def test_critic_rejects_unverified_skills(sample_profile):
    """Critic must reject bullets claiming skills not present in verified profile."""
    bullet = BulletRewrite(
        original_evidence="Maintained Python web APIs.",
        improved_bullet="Engineered high-performance microservices using Rust and Haskell.",
        highlighted_skills=["rust", "haskell"],
        rationale="Highlighted backend skills.",
    )

    valid, reason = deterministic_verify_bullet(bullet, sample_profile)
    assert valid is False
    assert "not present in candidate verified profile" in (reason or "")


def test_critic_rejects_invented_metrics(sample_profile):
    """Critic must reject bullets introducing invented numbers or percentages."""
    bullet = BulletRewrite(
        original_evidence="Maintained Python web APIs.",
        improved_bullet="Overhauled Python web APIs increasing throughput by 450% and cutting latency 3x.",
        highlighted_skills=["python"],
        rationale="Highlighted performance gains.",
    )

    valid, reason = deterministic_verify_bullet(bullet, sample_profile)
    assert valid is False
    assert "Invented metric" in (reason or "")


def test_critic_accepts_grounded_bullet(sample_profile):
    """Critic must accept rewrites that strictly preserve facts and evidence."""
    bullet = BulletRewrite(
        original_evidence="Maintained Python web APIs.",
        improved_bullet="Maintained and enhanced core Python web APIs to support business workflows.",
        highlighted_skills=["python"],
        rationale="Grounded rewrite.",
    )

    valid, reason = deterministic_verify_bullet(bullet, sample_profile)
    assert valid is True
    assert reason is None


def test_learning_plan_taxonomy_check(repo):
    """Critic must drop learning goals whose skill is not in the taxonomy."""
    goals = [
        LearningGoal(
            skill_slug="python",
            skill_name="Python",
            rationale="Standard skill",
            prerequisites=[],
            recommended_order=1,
        ),
        LearningGoal(
            skill_slug="fictional-hyper-ai-quantum-language",
            skill_name="Fictional Hyper AI",
            rationale="Fake skill",
            prerequisites=[],
            recommended_order=2,
        ),
    ]

    valid_goals, removed = deterministic_verify_learning_plan(goals, repo)
    assert len(valid_goals) == 1
    assert valid_goals[0].skill_slug == "python"
    assert len(removed) == 1
    assert "not in taxonomy" in removed[0]


@pytest.mark.asyncio
async def test_coach_degradation_without_llm_raises_503(sample_profile):
    """Exit Criterion 6-C: With no LLM, Coach raises ServiceUnavailable (503 problem+json)."""
    agent = CoachAgent(enable_llm=False)

    with pytest.raises(ServiceUnavailable) as exc_info:
        await agent.coach(
            candidate_id="candidate_0000",
            job_id="job_0001",
            profile_data=sample_profile,
        )

    assert exc_info.value.http_status == 503
    assert exc_info.value.code == "service_unavailable"


@pytest.mark.asyncio
async def test_coach_cache_exit_criterion_6_d(sample_profile):
    """Exit Criterion 6-D: Repeat request for same candidate+job makes 0 LLM calls."""
    agent = CoachAgent(enable_llm=False)

    # Pre-populate cache directly to test cache hit behavior
    cache_key = "candidate_0000::job_0001"
    cached_report = CoachReport(
        candidate_id="candidate_0000",
        job_id="job_0001",
        learning_plan=[],
        interview_questions=[],
        bullet_rewrites=[],
        removed_claims=[],
    )
    agent._cache[cache_key] = cached_report

    # Should hit cache immediately without raising ServiceUnavailable!
    result = await agent.coach("candidate_0000", job_id="job_0001")
    assert result == cached_report
