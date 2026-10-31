"""Unit tests for SearchAgent, planning, tools, and query caching (Milestone 6)."""

from __future__ import annotations

import pytest

from talentgraph.agents.search.agent import SearchAgent
from talentgraph.agents.search.plan import keyword_plan
from talentgraph.db.repositories.taxonomy import get_taxonomy_repository


@pytest.fixture
def repo():
    return get_taxonomy_repository()


def test_keyword_plan_extraction(repo):
    """Test rule-based deterministic search query planner."""
    plan = keyword_plan("Senior Python developer with 5+ years experience and Redis", repo)

    assert plan.seniority == "senior"
    assert plan.min_years == 5.0
    assert "python" in plan.must_skills or "redis" in plan.must_skills


def test_keyword_plan_should_clauses(repo):
    """Test partition of must vs should skills via keyword parsing."""
    plan = keyword_plan("Python backend engineer, ideally Redis and nice to have Docker", repo)

    assert "python" in plan.must_skills
    assert "redis" in plan.should_skills or "docker" in plan.should_skills


@pytest.mark.asyncio
async def test_search_agent_offline_execution():
    """Test SearchAgent end-to-end execution with deterministic planner (no LLM)."""
    agent = SearchAgent(enable_llm=False)

    plan, hits, used_llm = await agent.search("Senior Python developer with CI/CD", limit=5)

    assert used_llm is False
    assert len(hits) > 0
    assert hits[0].score >= 0.0
    # Every hit should have candidate_id and matched skills or citations
    top_hit = hits[0]
    assert top_hit.candidate_id.startswith("candidate_")
    assert isinstance(top_hit.citations, dict)


@pytest.mark.asyncio
async def test_search_agent_cache_exit_criterion_6_d():
    """Exit Criterion 6-D: Repeat request for the same query hits cache with 0 LLM calls."""
    agent = SearchAgent(enable_llm=False)
    query = "Data engineer with PyTorch and Pandas"

    # First call
    plan1, hits1, used1 = await agent.search(query, limit=5)

    # Second call (must hit in-memory cache)
    cache_key = f"{query.strip().lower()}::5"
    assert cache_key in agent._query_cache

    plan2, hits2, used2 = await agent.search(query, limit=5)

    assert plan1 == plan2
    assert [h.candidate_id for h in hits1] == [h.candidate_id for h in hits2]
