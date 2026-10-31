"""Unit tests for MatchingAgent, scoring, thresholds, and gap analysis (Steps 4.2 - 4.5)."""

from uuid import uuid4

import pytest

from talentgraph.agents.matching.agent import MatchingAgent
from talentgraph.agents.matching.scoring import (
    calculate_depth,
    calculate_match_score,
    compute_skill_similarity,
)
from talentgraph.agents.matching.thresholds import resolve_threshold
from talentgraph.core.schemas.matching import (
    JobRequirement,
    JobRequirements,
)
from talentgraph.core.schemas.messages import AgentMessage
from talentgraph.core.schemas.skills import NormalizedSkill, SkillProfile
from talentgraph.db.repositories.taxonomy import get_taxonomy_repository


@pytest.fixture
def repo():
    return get_taxonomy_repository()


def test_depth_calculation() -> None:
    skill = NormalizedSkill(
        slug="python",
        name="Python",
        years=2.0,
        proficiency=3,
    )
    # min_years = 4.0 -> 2.0 / 4.0 = 0.5
    assert calculate_depth(skill, min_years=4.0) == 0.5
    # min_years = 1.0 -> capped at 1.0
    assert calculate_depth(skill, min_years=1.0) == 1.0
    # min_years is None -> uses years / 3.0 = 2.0 / 3.0
    assert calculate_depth(skill, min_years=None) == pytest.approx(2.0 / 3.0)


def test_compute_skill_similarity(repo) -> None:
    # Exact match
    sim, mtype = compute_skill_similarity("python", "python", repo=repo)
    assert sim == 1.0
    assert mtype == "exact"

    # Descendant: deep-learning -> machine-learning-frameworks
    sim_desc, mtype_desc = compute_skill_similarity(
        "deep-learning", "machine-learning-frameworks", repo=repo
    )
    assert sim_desc == 0.9
    assert mtype_desc == "descendant"

    # Ancestor: machine-learning-frameworks -> deep-learning
    sim_anc, mtype_anc = compute_skill_similarity(
        "machine-learning-frameworks", "deep-learning", repo=repo
    )
    assert sim_anc == 0.6
    assert mtype_anc == "ancestor_or_sibling"

    # Sibling in same subcategory or shared parent
    sim_sib, mtype_sib = compute_skill_similarity("docker", "kubernetes", repo=repo)
    assert sim_sib == 0.6
    assert mtype_sib == "ancestor_or_sibling"

    # Completely unrelated missing
    sim_miss, mtype_miss = compute_skill_similarity("python", "nursing", repo=repo)
    assert sim_miss == 0.0
    assert mtype_miss == "missing"


def test_exit_criterion_4_b_breakdown_sums_to_skill_score(repo) -> None:
    """Exit Criterion 4-B: MatchResult breakdown sums to reported skill score."""
    profile = SkillProfile(
        skills=[
            NormalizedSkill(slug="python", name="Python", years=4.0, proficiency=4),
            NormalizedSkill(slug="docker", name="Docker", years=2.0, proficiency=3),
            NormalizedSkill(slug="postgresql", name="PostgreSQL", years=3.0, proficiency=3),
        ]
    )

    job = JobRequirements(
        title="Backend Engineer",
        seniority="senior",
        min_total_experience_years=5.0,
        requirements=[
            JobRequirement(
                skill_slug="python", name="Python", required=True, importance=5, min_years=3.0
            ),
            JobRequirement(
                skill_slug="kubernetes",
                name="Kubernetes",
                required=True,
                importance=4,
                min_years=2.0,
            ),
            JobRequirement(
                skill_slug="postgresql",
                name="PostgreSQL",
                required=True,
                importance=4,
                min_years=2.0,
            ),
            JobRequirement(skill_slug="redis", name="Redis", required=False, importance=3),
        ],
    )

    result = calculate_match_score(profile, job, repo=repo)

    # 4-B check: sum of breakdown contributions must equal skill_score
    breakdown_sum = sum(b.contribution for b in result.breakdown)
    reported_skill_score = result.components["skill_score"]

    assert breakdown_sum == pytest.approx(reported_skill_score, abs=1e-4)
    assert result.score > 0.0
    assert 0.0 <= result.score <= 1.0


def test_missing_required_skill_penalty(repo) -> None:
    profile = SkillProfile(
        skills=[
            NormalizedSkill(slug="python", name="Python", years=3.0, proficiency=3),
        ]
    )
    # Job requires kubernetes (imp 5) which is missing -> should incur 0.10 penalty
    job = JobRequirements(
        title="Cloud Engineer",
        requirements=[
            JobRequirement(skill_slug="python", name="Python", required=True, importance=5),
            JobRequirement(skill_slug="kubernetes", name="Kubernetes", required=True, importance=5),
        ],
    )
    result = calculate_match_score(profile, job, repo=repo)
    assert result.components["penalty"] == pytest.approx(0.10)


def test_threshold_resolution() -> None:
    val, name = resolve_threshold("precision")
    assert val == 0.75
    assert name == "precision"

    val_b, name_b = resolve_threshold("balanced")
    assert val_b == 0.60
    assert name_b == "balanced"

    val_r, name_r = resolve_threshold("recall")
    assert val_r == 0.45
    assert name_r == "recall"

    val_c, name_c = resolve_threshold(0.82)
    assert val_c == 0.82
    assert name_c is None

    with pytest.raises(ValueError):
        resolve_threshold("invalid_preset")

    with pytest.raises(ValueError):
        resolve_threshold(1.5)


@pytest.mark.asyncio
async def test_matching_agent_full_flow(repo) -> None:
    agent = MatchingAgent(repo=repo)
    profile = SkillProfile(
        candidate_id=uuid4(),
        skills=[
            NormalizedSkill(slug="python", name="Python", years=5.0, proficiency=4),
            NormalizedSkill(slug="fastapi", name="FastAPI", years=3.0, proficiency=4),
            NormalizedSkill(slug="docker", name="Docker", years=3.0, proficiency=3),
        ],
        meta={"total_experience_years": 5.0},
    )

    job = JobRequirements(
        job_id="job_test",
        title="Senior Python Backend Developer",
        seniority="senior",
        min_total_experience_years=5.0,
        requirements=[
            JobRequirement(
                skill_slug="python", name="Python", required=True, importance=5, min_years=4.0
            ),
            JobRequirement(
                skill_slug="fastapi", name="FastAPI", required=True, importance=4, min_years=2.0
            ),
            JobRequirement(
                skill_slug="kubernetes",
                name="Kubernetes",
                required=True,
                importance=4,
                min_years=2.0,
            ),
        ],
    )

    result = await agent.match(profile, job, threshold="balanced")

    assert result.is_match is True
    assert result.threshold == 0.60
    assert result.preset == "balanced"
    assert len(result.breakdown) == 3

    # Check Exit Criterion 4-B
    assert sum(b.contribution for b in result.breakdown) == pytest.approx(
        result.components["skill_score"], abs=1e-4
    )

    # Check Gaps & Upskilling hints
    assert len(result.gaps) > 0
    k8s_gap = next(g for g in result.gaps if g.skill_slug == "kubernetes")
    assert k8s_gap.required is True
    # Should recommend upskilling from Docker
    assert any("Docker" in hint for hint in k8s_gap.upskilling_hints)


@pytest.mark.asyncio
async def test_matching_agent_rank(repo) -> None:
    agent = MatchingAgent(repo=repo)

    strong_cand = SkillProfile(
        candidate_id=uuid4(),
        skills=[
            NormalizedSkill(slug="python", name="Python", years=6.0, proficiency=5),
            NormalizedSkill(slug="fastapi", name="FastAPI", years=4.0, proficiency=4),
            NormalizedSkill(slug="postgresql", name="PostgreSQL", years=5.0, proficiency=4),
        ],
        meta={"total_experience_years": 6.0},
    )

    weak_cand = SkillProfile(
        candidate_id=uuid4(),
        skills=[
            NormalizedSkill(slug="html", name="HTML", years=1.0, proficiency=2),
        ],
        meta={"total_experience_years": 1.0},
    )

    job = JobRequirements(
        title="Senior Backend Engineer",
        seniority="senior",
        requirements=[
            JobRequirement(skill_slug="python", name="Python", required=True, importance=5),
            JobRequirement(skill_slug="fastapi", name="FastAPI", required=True, importance=4),
        ],
    )

    ranked = await agent.rank([weak_cand, strong_cand], job)
    assert len(ranked) == 2
    assert ranked[0].score > ranked[1].score
    assert ranked[0].candidate_id == str(strong_cand.candidate_id)


@pytest.mark.asyncio
async def test_matching_agent_message_protocol(repo) -> None:
    agent = MatchingAgent(repo=repo)
    profile = SkillProfile(
        skills=[NormalizedSkill(slug="python", name="Python", years=3.0, proficiency=3)]
    )
    job = JobRequirements(
        requirements=[
            JobRequirement(skill_slug="python", name="Python", required=True, importance=5)
        ]
    )

    msg = AgentMessage(
        trace_id=uuid4(),
        sender="orchestrator",
        recipient="matcher",
        type="task",
        payload={"profile": profile.model_dump(), "job": job.model_dump(), "threshold": "balanced"},
    )

    res = await agent.handle(msg)
    assert res.status == "ok"
    assert res.data is not None
    assert res.data["score"] > 0.0
    assert res.quality.score > 0.0
