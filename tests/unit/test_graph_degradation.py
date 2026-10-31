"""Unit tests for LangGraph pipeline and degradation edges (Exit Criterion 4-C, Step 4.7)."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from talentgraph.agents.matching.agent import MatchingAgent
from talentgraph.agents.normalization.agent import NormalizationAgent
from talentgraph.core.schemas.matching import JobRequirement, JobRequirements
from talentgraph.core.schemas.resume import Extracted, ParsedResume, Personal, Skill
from talentgraph.db.repositories.taxonomy import get_taxonomy_repository
from talentgraph.orchestrator.graph import run_match_pipeline
from talentgraph.orchestrator.state import PipelineState


@pytest.fixture
def sample_resume() -> ParsedResume:
    return ParsedResume(
        personal=Personal(
            name=Extracted(value="Alice Smith"),
            email=Extracted(value="alice@example.com"),
        ),
        skills=[Skill(raw="Python"), Skill(raw="FastAPI")],
    )


@pytest.fixture
def sample_job() -> JobRequirements:
    return JobRequirements(
        title="Python Engineer",
        requirements=[
            JobRequirement(skill_slug="python", name="Python", required=True, importance=5)
        ],
    )


@pytest.mark.asyncio
async def test_exit_criterion_4_c_normalizer_failure(
    sample_resume: ParsedResume, sample_job: JobRequirements
) -> None:
    """With the normalizer forced to fail, pipeline returns partial with earlier outputs intact."""
    mock_normalizer = AsyncMock(spec=NormalizationAgent)
    mock_normalizer.name = "normalizer"
    # Normalizer fails
    mock_normalizer.handle.side_effect = RuntimeError("Chroma/DB timeout in normalizer")

    state = PipelineState(
        trace_id=uuid4(),
        parsed_resume=sample_resume,
        job=sample_job,
    )

    result_state = await run_match_pipeline(state, normalizer=mock_normalizer)

    # Status must degrade to partial
    assert result_state.status == "partial"

    # Earlier parsed_resume must remain intact
    assert result_state.parsed_resume is not None
    assert result_state.parsed_resume.personal.name.value == "Alice Smith"

    # Raw skills retained
    assert "Python" in result_state.raw_skills
    assert "FastAPI" in result_state.raw_skills

    # Matcher was skipped because normalization failed
    assert result_state.match_result is None

    # Error recorded
    assert any(e.agent == "normalizer" for e in result_state.errors)


@pytest.mark.asyncio
async def test_exit_criterion_4_c_matcher_failure(
    sample_resume: ParsedResume, sample_job: JobRequirements
) -> None:
    """With the matcher forced to fail, pipeline returns partial with earlier outputs intact."""
    mock_matcher = AsyncMock(spec=MatchingAgent)
    mock_matcher.name = "matcher"
    mock_matcher.handle.side_effect = RuntimeError("Embedding index offline")

    repo = get_taxonomy_repository()
    normalizer = NormalizationAgent(repo=repo)

    state = PipelineState(
        trace_id=uuid4(),
        parsed_resume=sample_resume,
        job=sample_job,
    )

    result_state = await run_match_pipeline(state, normalizer=normalizer, matcher=mock_matcher)

    # Status must degrade to partial
    assert result_state.status == "partial"

    # Earlier outputs intact
    assert result_state.parsed_resume is not None
    assert result_state.parsed_resume.personal.name.value == "Alice Smith"

    assert result_state.skill_profile is not None
    assert any(s.slug == "python" for s in result_state.skill_profile.skills)

    # Match result is None
    assert result_state.match_result is None

    # Matcher error recorded
    assert any(e.agent == "matcher" for e in result_state.errors)


@pytest.mark.asyncio
async def test_pipeline_success_and_blind_mode(
    sample_resume: ParsedResume, sample_job: JobRequirements
) -> None:
    repo = get_taxonomy_repository()
    normalizer = NormalizationAgent(repo=repo)
    matcher = MatchingAgent(repo=repo)

    state = PipelineState(
        trace_id=uuid4(),
        parsed_resume=sample_resume,
        job=sample_job,
        blind=True,  # Test blind branch
    )

    result_state = await run_match_pipeline(state, normalizer=normalizer, matcher=matcher)

    assert result_state.status == "ok"
    assert result_state.parsed_resume is not None
    # Blind redaction occurred
    assert result_state.parsed_resume.personal.name.value == "[REDACTED_NAME]"
    assert result_state.match_result is not None
    assert result_state.match_result.score > 0.0
