"""Unit tests for Step 4.1: JobParser and matching schemas."""

from pathlib import Path

import pytest

from talentgraph.agents.matching.job_parser import InMemoryJDCache, JobParser
from talentgraph.core.schemas.matching import (
    RawJobExtraction,
)
from talentgraph.llm.fake import FakeLLM


@pytest.mark.asyncio
async def test_load_from_ground_truth() -> None:
    job = JobParser.load_from_ground_truth("job_000")
    assert job.job_id == "job_000"
    assert "Backend" in job.title
    assert job.role_family == "engineering"
    assert job.seniority == "principal"
    assert len(job.requirements) > 0
    assert any(r.skill_slug == "python" for r in job.requirements)
    python_req = next(r for r in job.requirements if r.skill_slug == "python")
    assert python_req.importance == 5
    assert python_req.required is True
    assert python_req.min_years == 3.0


@pytest.mark.asyncio
async def test_job_parser_with_fake_llm(tmp_path: Path) -> None:
    fake_llm = FakeLLM(tmp_path)
    fake_llm.register(
        RawJobExtraction,
        {
            "title": "Senior Python Developer",
            "company": "Tech Corp",
            "seniority": "senior",
            "role_family": "engineering",
            "min_total_experience_years": 5.0,
            "education": ["Bachelor's Degree"],
            "requirements": [
                {
                    "name": "Python",
                    "required": True,
                    "importance": 5,
                    "min_years": 4.0,
                },
                {
                    "name": "Docker",
                    "required": False,
                    "importance": 3,
                    "min_years": 1.0,
                },
                {
                    "name": "python",  # Duplicate to test deduplication
                    "required": True,
                    "importance": 4,
                    "min_years": 2.0,
                },
            ],
        },
    )

    cache = InMemoryJDCache()
    parser = JobParser(llm=fake_llm, cache=cache)

    jd_text = "Looking for a Senior Python Developer with 5+ years experience and Docker."
    parsed = await parser.parse(jd_text, job_id="test_job_1")

    assert parsed.job_id == "test_job_1"
    assert parsed.title == "Senior Python Developer"
    assert parsed.company == "Tech Corp"
    assert parsed.seniority == "senior"
    assert parsed.min_total_experience_years == 5.0

    # Verify deduplication
    slugs = [r.skill_slug for r in parsed.requirements]
    assert slugs.count("python") == 1
    python_req = next(r for r in parsed.requirements if r.skill_slug == "python")
    assert python_req.importance == 5  # Max importance retained
    assert python_req.min_years == 4.0

    # Cache hit check
    assert len(fake_llm.calls) == 1
    cached_parsed = await parser.parse(jd_text, job_id="test_job_1")
    assert cached_parsed.title == "Senior Python Developer"
    assert len(fake_llm.calls) == 1  # No additional LLM call


@pytest.mark.asyncio
async def test_job_parser_empty_text(tmp_path: Path) -> None:
    fake_llm = FakeLLM(tmp_path)
    parser = JobParser(llm=fake_llm)
    parsed = await parser.parse("", job_id="empty_job")
    assert parsed.raw_text_length == 0
    assert len(parsed.requirements) == 0
