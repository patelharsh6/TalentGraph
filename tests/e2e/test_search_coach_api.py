"""End-to-end API tests for POST /api/v1/search and POST /api/v1/coach (Milestone 6).

Verifies:
- Exit Criterion 6-C: With no LLM, /search returns 'partial' from keyword planner; /coach returns 503 problem+json, not a 500.
- Exit Criterion 6-D: A repeat request for the same query or candidate+job makes 0 LLM calls (cache test).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from talentgraph.agents.coach.agent import CoachAgent
from talentgraph.agents.search.agent import SearchAgent
from talentgraph.api.main import create_app
from talentgraph.api.schemas import BulletRewrite, CoachReport, InterviewQuestion, LearningGoal
from talentgraph.config import Settings
from talentgraph.db.repositories.taxonomy import get_taxonomy_repository

pytestmark = [pytest.mark.unit]

ROOT = Path(__file__).resolve().parents[2]
FIXTURES_DIR = ROOT / "tests" / "fixtures"


@pytest.fixture
def app(monkeypatch: pytest.MonkeyPatch) -> FastAPI:
    """FastAPI test app configured for offline execution."""
    monkeypatch.setenv("API_KEY", "test-key")
    from talentgraph.config import get_settings
    get_settings.cache_clear()
    test_settings = get_settings()
    application = create_app()
    repo = get_taxonomy_repository(test_settings.taxonomy_dir)

    # SearchAgent with enable_llm=False to test graceful degradation (Exit Criterion 6-C)
    application.state.search_agent = SearchAgent(
        settings=test_settings,
        repo=repo,
        enable_llm=False,
    )

    # CoachAgent with enable_llm=False to test 503 problem+json (Exit Criterion 6-C)
    application.state.coach_agent = CoachAgent(
        settings=test_settings,
        repo=repo,
        enable_llm=False,
    )

    return application


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app, headers={"X-API-Key": "test-key"})


def test_search_endpoint_degradation_partial(client: TestClient):
    """Exit Criterion 6-C: With no LLM, /search returns 'partial' from keyword planner."""
    resp = client.post(
        "/api/v1/search",
        json={"query": "Senior Python engineer with AWS and Docker", "limit": 5},
    )
    assert resp.status_code == 200
    body = resp.json()

    assert "data" in body
    assert "meta" in body
    # Must report partial status due to deterministic keyword fallback without LLM
    assert body["meta"]["status"] == "partial"
    assert body["data"]["total_candidates"] > 0
    assert len(body["data"]["results"]) <= 5
    assert "plan" in body["data"]


def test_search_endpoint_cache_exit_criterion_6_d(client: TestClient, app: FastAPI):
    """Exit Criterion 6-D: Repeat request for same query hits cache with 0 LLM calls."""
    query = "Data engineer with PyTorch and Pandas"
    resp1 = client.post("/api/v1/search", json={"query": query, "limit": 5})
    assert resp1.status_code == 200

    # Verify cache key exists in agent
    cache_key = f"{query.strip().lower()}::5"
    assert cache_key in app.state.search_agent._query_cache

    # Second call should return identical cached result
    resp2 = client.post("/api/v1/search", json={"query": query, "limit": 5})
    assert resp2.status_code == 200
    assert resp1.json()["data"]["results"] == resp2.json()["data"]["results"]


def test_coach_endpoint_degradation_503_problem_json(client: TestClient):
    """Exit Criterion 6-C: With no LLM, /coach returns 503 problem+json, not a 500."""
    resp = client.post(
        "/api/v1/coach",
        json={"candidate_id": "candidate_0000", "job_id": "job_0001"},
    )

    # Must return 503, NOT 500
    assert resp.status_code == 503
    assert resp.headers.get("content-type") == "application/problem+json"

    problem = resp.json()
    assert problem["status"] == 503
    assert problem["title"] == "Service unavailable"
    assert "service_unavailable" in problem["type"]


def test_coach_endpoint_cache_and_report(client: TestClient, app: FastAPI):
    """Exit Criterion 6-D: Pre-cached or repeat candidate+job request returns CoachReport with 0 LLM calls."""
    cache_key = "candidate_0000::job_0001"
    mock_report = CoachReport(
        candidate_id="candidate_0000",
        job_id="job_0001",
        learning_plan=[
            LearningGoal(
                skill_slug="kubernetes",
                skill_name="Kubernetes",
                rationale="Required for deployment",
                prerequisites=["docker"],
                recommended_order=1,
            )
        ],
        interview_questions=[
            InterviewQuestion(
                requirement_name="Kubernetes",
                question="How do you manage cluster rollouts?",
                target_competency="Kubernetes",
                preparation_tip="Discuss rolling updates and deployments.",
            )
        ],
        bullet_rewrites=[
            BulletRewrite(
                original_evidence="Maintained Python services.",
                improved_bullet="Maintained and optimized Python services for cloud production.",
                highlighted_skills=["python"],
                rationale="Factual rewrite.",
            )
        ],
        removed_claims=["Removed hallucinated metric claim."],
        revisions_count=1,
    )
    # Seed cache
    app.state.coach_agent._cache[cache_key] = mock_report

    # Hit endpoint: should succeed with 200 returning cached report without raising 503!
    resp = client.post(
        "/api/v1/coach",
        json={"candidate_id": "candidate_0000", "job_id": "job_0001"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]

    assert data["candidate_id"] == "candidate_0000"
    assert len(data["learning_plan"]) == 1
    assert data["learning_plan"][0]["skill_slug"] == "kubernetes"
    assert len(data["interview_questions"]) == 1
    assert len(data["bullet_rewrites"]) == 1
    assert len(data["removed_claims"]) == 1
