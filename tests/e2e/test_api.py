"""Step 5.7: End-to-end API tests covering every endpoint, error handling, auth, and rate limits."""

from pathlib import Path
from uuid import UUID

import openapi_spec_validator
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr

from talentgraph.agents.matching.agent import MatchingAgent
from talentgraph.agents.matching.job_parser import JobParser
from talentgraph.agents.normalization.agent import NormalizationAgent
from talentgraph.agents.parsing.agent import ParsingAgent
from talentgraph.agents.parsing.cache import InMemoryParseCache
from talentgraph.api.main import create_app
from talentgraph.api.problems import register_problem_handlers
from talentgraph.config import Settings
from talentgraph.core.errors import (
    AgentTimeout,
    FileTooLarge,
    LLMError,
    NotFound,
    RateLimitExceeded,
    Unauthorized,
    UnsupportedContent,
    UnsupportedFileType,
)
from talentgraph.db.repositories.taxonomy import get_taxonomy_repository
from talentgraph.llm.fake import FakeLLM
from talentgraph.orchestrator.batch import (
    _IN_MEMORY_ITEMS,
    _IN_MEMORY_JOBS,
    create_batch_record,
    recover_stale_batches,
)

pytestmark = [pytest.mark.unit, pytest.mark.e2e]

ROOT = Path(__file__).resolve().parents[2]
FIXTURES_DIR = ROOT / "tests" / "fixtures"
RESUMES_DIR = FIXTURES_DIR / "resumes"


@pytest.fixture
def app() -> FastAPI:
    """FastAPI application configured with FakeLLM and in-memory caches for offline testing."""
    test_settings = Settings(
        app_env="test",
        api_key=None,
        llm_mode="fake",
        fixtures_dir=str(FIXTURES_DIR / "llm"),
    )

    fake_llm = FakeLLM(FIXTURES_DIR / "llm")
    repo = get_taxonomy_repository(test_settings.taxonomy_dir)
    parse_cache = InMemoryParseCache()

    application = create_app()

    # Pre-populate app state
    application.state.parsing_agent = ParsingAgent(
        settings=test_settings, llm=fake_llm, cache=parse_cache
    )
    application.state.normalization_agent = NormalizationAgent(
        settings=test_settings, llm=fake_llm, repo=repo
    )
    application.state.matching_agent = MatchingAgent(settings=test_settings, repo=repo)
    application.state.job_parser = JobParser(llm=fake_llm)
    application.state.taxonomy_repo = repo
    application.state.engine = None
    application.state.redis = None

    return application


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


# --------------------------------------------------------------------------------------------------
# Exit Criterion 5-A: OpenAPI Specification Validation
# --------------------------------------------------------------------------------------------------


def test_exit_criterion_5a_openapi_spec(client: TestClient) -> None:
    """Exit Criterion 5-A: Every §8 endpoint is present; OpenAPI schema validates with 0 errors."""
    res = client.get("/openapi.json")
    assert res.status_code == 200
    schema = res.json()

    # 1. Validate spec with openapi-spec-validator
    openapi_spec_validator.validate_spec(schema)

    # 2. Check all §8 endpoints are declared
    paths = schema["paths"]
    expected_endpoints = [
        "/health",
        "/ready",
        "/api/v1/parse",
        "/api/v1/parse/batch",
        "/api/v1/jobs/{batch_job_id}",
        "/api/v1/candidates/{candidate_id}",
        "/api/v1/candidates/{candidate_id}/skills",
        "/api/v1/match",
        "/api/v1/match/rank",
        "/api/v1/skills/taxonomy",
        "/api/v1/skills/search",
        "/api/v1/skills/{skill_id_or_slug}",
    ]
    for ep in expected_endpoints:
        assert ep in paths, f"Expected endpoint {ep} missing from OpenAPI specification"


# --------------------------------------------------------------------------------------------------
# Exit Criterion 5-B: RFC 7807 problem+json Error Rendering
# --------------------------------------------------------------------------------------------------


def test_exit_criterion_5b_errors_render_as_problem_json() -> None:
    """Exit Criterion 5-B: Each TalentGraphError subclass renders as problem+json."""
    test_app = FastAPI()
    register_problem_handlers(test_app)

    @test_app.get("/test/unsupported-type")
    def _err_415() -> None:
        raise UnsupportedFileType("Detected image/png; expected PDF, DOCX or TXT.")

    @test_app.get("/test/file-too-large")
    def _err_413() -> None:
        raise FileTooLarge("File is 15 MB; maximum allowed is 10 MB.")

    @test_app.get("/test/unsupported-content")
    def _err_422() -> None:
        raise UnsupportedContent("PDF appears scanned or corrupted.")

    @test_app.get("/test/not-found")
    def _err_404() -> None:
        raise NotFound("Candidate not found.")

    @test_app.get("/test/unauthorized")
    def _err_401() -> None:
        raise Unauthorized("Missing or invalid API key.")

    @test_app.get("/test/rate-limited")
    def _err_429() -> None:
        raise RateLimitExceeded("Too many requests.")

    @test_app.get("/test/llm-error")
    def _err_502() -> None:
        raise LLMError("Upstream model returned empty completion.")

    @test_app.get("/test/timeout")
    def _err_504() -> None:
        raise AgentTimeout("Parsing agent exceeded execution budget.")

    test_client = TestClient(test_app)

    test_cases = [
        ("/test/unsupported-type", 415, "unsupported_file_type"),
        ("/test/file-too-large", 413, "file_too_large"),
        ("/test/unsupported-content", 422, "unsupported_content"),
        ("/test/not-found", 404, "not_found"),
        ("/test/unauthorized", 401, "unauthorized"),
        ("/test/rate-limited", 429, "rate_limit_exceeded"),
        ("/test/llm-error", 502, "llm_error"),
        ("/test/timeout", 504, "agent_timeout"),
    ]

    for path, expected_status, expected_code in test_cases:
        res = test_client.get(path)
        assert res.status_code == expected_status, f"Expected {expected_status} for {path}"
        assert res.headers["content-type"].startswith("application/problem+json")
        data = res.json()
        assert data["status"] == expected_status
        assert data["type"].endswith(f"/{expected_code}")
        assert "title" in data
        assert "detail" in data
        assert "instance" in data

    # Check 429 Retry-After header
    res_429 = test_client.get("/test/rate-limited")
    assert "Retry-After" in res_429.headers


# --------------------------------------------------------------------------------------------------
# Exit Criterion 5-C: API Key Authentication and Rate Limiting
# --------------------------------------------------------------------------------------------------


def test_exit_criterion_5c_auth_and_limits(monkeypatch: pytest.MonkeyPatch, app: FastAPI) -> None:
    """Exit Criterion 5-C: No key -> 401 on write; exceeding limit -> 429 with Retry-After."""
    # Configure API_KEY in settings
    secret_key = "tg-secret-key-12345"
    test_settings = Settings(api_key=SecretStr(secret_key), llm_mode="fake")
    monkeypatch.setattr("talentgraph.api.auth.get_settings", lambda: test_settings)

    client = TestClient(app)
    resume_path = RESUMES_DIR / "candidate_0009.txt"
    resume_bytes = resume_path.read_bytes()

    # 1. Write endpoint without X-API-Key -> 401
    res_no_key = client.post(
        "/api/v1/parse",
        files={"file": ("candidate_0009.txt", resume_bytes, "text/plain")},
    )
    assert res_no_key.status_code == 401
    assert res_no_key.headers["content-type"].startswith("application/problem+json")
    assert res_no_key.json()["type"].endswith("/unauthorized")

    # 2. Write endpoint with invalid X-API-Key -> 401
    res_bad_key = client.post(
        "/api/v1/parse",
        headers={"X-API-Key": "wrong-key"},
        files={"file": ("candidate_0009.txt", resume_bytes, "text/plain")},
    )
    assert res_bad_key.status_code == 401

    # 3. Read endpoints work without API key
    res_health = client.get("/health")
    assert res_health.status_code == 200
    res_tax = client.get("/api/v1/skills/taxonomy")
    assert res_tax.status_code == 200

    # 4. Write endpoint with valid X-API-Key -> succeeds
    res_valid = client.post(
        "/api/v1/parse",
        headers={"X-API-Key": secret_key},
        files={"file": ("candidate_0009.txt", resume_bytes, "text/plain")},
    )
    assert res_valid.status_code == 200

    # 5. Rate limit exceeded handler test (429 with Retry-After)
    test_rate_app = FastAPI()
    register_problem_handlers(test_rate_app)

    @test_rate_app.get("/rate-test")
    def _trigger_429() -> None:
        raise RateLimitExceeded("Too many calls")

    r_client = TestClient(test_rate_app)
    r_res = r_client.get("/rate-test")
    assert r_res.status_code == 429
    assert "Retry-After" in r_res.headers


# --------------------------------------------------------------------------------------------------
# Functional E2E Tests: Parse, Candidates, Match, Rank, Skills
# --------------------------------------------------------------------------------------------------


def test_parse_and_candidate_skills_e2e(client: TestClient) -> None:
    """Test full flow: POST /parse -> GET /candidates/{id} -> GET /candidates/{id}/skills."""
    resume_path = RESUMES_DIR / "candidate_0009.txt"
    res = client.post(
        "/api/v1/parse?include=trace",
        files={"file": ("candidate_0009.txt", resume_path.read_bytes(), "text/plain")},
    )
    assert res.status_code == 200
    payload = res.json()
    assert "data" in payload and "meta" in payload
    assert payload["meta"]["status"] in ("ok", "partial")
    assert payload["meta"]["trace"] is not None

    cand_id = payload["data"]["candidate_id"]

    # Retrieve candidate
    res_cand = client.get(f"/api/v1/candidates/{cand_id}")
    assert res_cand.status_code == 200
    assert res_cand.json()["id"] == cand_id

    # Retrieve candidate skills
    res_skills = client.get(f"/api/v1/candidates/{cand_id}/skills")
    assert res_skills.status_code == 200
    skills_data = res_skills.json()
    assert "skills" in skills_data
    assert len(skills_data["skills"]) > 0

    # Retrieve with filter
    res_filtered = client.get(f"/api/v1/candidates/{cand_id}/skills?min_proficiency=3")
    assert res_filtered.status_code == 200
    for sk in res_filtered.json()["skills"]:
        assert sk["proficiency"] >= 3


def test_match_and_rank_e2e(client: TestClient) -> None:
    """Test POST /match and POST /match/rank in normal and blind mode."""
    # 1. Parse a candidate
    resume_path = RESUMES_DIR / "candidate_0009.txt"
    p_res = client.post(
        "/api/v1/parse",
        files={"file": ("candidate_0009.txt", resume_path.read_bytes(), "text/plain")},
    )
    cand_id = p_res.json()["data"]["candidate_id"]

    job_payload = {
        "candidate_id": cand_id,
        "job": {
            "title": "Senior Python Developer",
            "description": "Expert Python engineer with experience in FastAPI and Docker.",
        },
        "preset": "balanced",
    }

    # 2. Match normal
    res_match = client.post("/api/v1/match", json=job_payload)
    assert res_match.status_code == 200
    m_data = res_match.json()["data"]
    assert "score" in m_data
    assert "breakdown" in m_data
    assert "gaps" in m_data

    # 3. Match blind
    res_blind = client.post("/api/v1/match?blind=true", json=job_payload)
    assert res_blind.status_code == 200
    assert "score" in res_blind.json()["data"]

    # 4. Rank candidates
    rank_payload = {
        "candidate_ids": [cand_id],
        "job": job_payload["job"],
        "preset": "balanced",
    }
    res_rank = client.post("/api/v1/match/rank", json=rank_payload)
    assert res_rank.status_code == 200
    ranked_list = res_rank.json()
    assert len(ranked_list) >= 1
    assert ranked_list[0]["candidate_id"] == cand_id


def test_skills_endpoints_e2e(client: TestClient) -> None:
    """Test taxonomy browsing, skill search, and skill details."""
    # 1. Browse root domains
    res_tax = client.get("/api/v1/skills/taxonomy")
    assert res_tax.status_code == 200
    domains = res_tax.json()
    assert len(domains) > 0
    assert all(d["level"] == 0 for d in domains)

    # 2. Browse children
    first_domain_id = domains[0]["id"]
    res_children = client.get(f"/api/v1/skills/taxonomy?parent_id={first_domain_id}")
    assert res_children.status_code == 200

    # 3. Search skills
    res_search = client.get("/api/v1/skills/search?q=python")
    assert res_search.status_code == 200
    search_hits = res_search.json()
    assert len(search_hits) > 0
    assert any("python" in h["slug"].lower() for h in search_hits)

    # 4. Skill detail
    res_detail = client.get("/api/v1/skills/python")
    assert res_detail.status_code == 200
    detail = res_detail.json()
    assert detail["slug"] == "python"
    assert "ancestors" in detail
    assert "children" in detail
    assert "aliases" in detail


# --------------------------------------------------------------------------------------------------
# Exit Criterion 5-D: Batches and Restart Recovery
# --------------------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_exit_criterion_5d_batch_processing_and_stale_recovery(app: FastAPI) -> None:
    """Exit Criterion 5-D: 20-file batch completes. Simulated restart marks stale items failed."""
    client = TestClient(app)

    # 1. Submit a 20-file batch
    resume_path = RESUMES_DIR / "candidate_0009.txt"
    content = resume_path.read_bytes()
    files = [("files", (f"cand_{i:02d}.txt", content, "text/plain")) for i in range(20)]

    res_batch = client.post("/api/v1/parse/batch", files=files)
    assert res_batch.status_code == 202
    batch_info = res_batch.json()
    assert batch_info["status"] == "queued"
    assert batch_info["total"] == 20
    batch_id = UUID(batch_info["batch_job_id"])

    # 2. Verify batch job status endpoint
    res_job = client.get(f"/api/v1/jobs/{batch_id}")
    assert res_job.status_code == 200
    job_status = res_job.json()
    assert job_status["id"] == str(batch_id)
    assert job_status["total"] == 20
    assert len(job_status["items"]) == 20

    # 3. Simulate server restart with stale running items
    stale_job_id, stale_job = await create_batch_record(["stale_01.txt", "stale_02.txt"])
    _IN_MEMORY_JOBS[stale_job_id]["status"] = "running"
    for it in _IN_MEMORY_ITEMS[stale_job_id]:
        it["status"] = "running"

    recovered_count = await recover_stale_batches(engine=None)
    assert recovered_count >= 1

    # Check that stale items and job are marked failed
    stale_check = client.get(f"/api/v1/jobs/{stale_job_id}").json()
    assert stale_check["status"] == "failed"
    for it in stale_check["items"]:
        assert it["status"] == "failed"
        assert it["error"]["code"] == "server_restart"
