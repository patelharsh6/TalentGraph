"""Steps 2.9–2.12: verifier, merge rules, ParsingAgent, degradation, errors and cache
(exit criteria 2-A, 2-C, 2-D, 2-E).

The resume here is hand-written so that the LLM extraction can be hand-written too: line numbers
are looked up from the prompt the agent would send, exactly as the real model sees them.
"""

from datetime import date
from pathlib import Path
from typing import Any, TypeVar

import pytest
from fastapi import FastAPI, UploadFile
from fastapi.testclient import TestClient
from pydantic import BaseModel

from talentgraph.agents.parsing.agent import ParsingAgent, quality_score
from talentgraph.agents.parsing.cache import InMemoryParseCache, cache_key
from talentgraph.agents.parsing.llm_extract import build_user_message, system_prompt
from talentgraph.agents.parsing.merge import build_resume
from talentgraph.agents.parsing.rules import Match, RuleResult
from talentgraph.agents.parsing.verify import EvidenceAligner, iter_grounded, verify_resume
from talentgraph.api.problems import register_problem_handlers
from talentgraph.config import Settings
from talentgraph.core.errors import LLMError, LLMQuotaExceeded
from talentgraph.core.schemas.resume import Extracted, ParsedResume, ResumeExtraction
from talentgraph.llm.fake import FakeLLM

T = TypeVar("T", bound=BaseModel)
TODAY = date(2026, 10, 13)

RESUME = """JANE ROE
jane.roe@example.com | (415) 555-0134 | Springfield, IL | https://github.com/janeroe

--- SUMMARY ---
Backend engineer with 6 years of experience
building data platforms.

--- EXPERIENCE ---
Senior Engineer | Acme Corp
  Jan 2021 – Present · Chicago, IL
  * Built the ingestion pipeline in Python
    handling 2 TB per day.
  * Led a team of four.
Engineer | Globex
  06/2018 – 12/2020 · Remote
  * Wrote services in Go.

--- EDUCATION ---
BSc in Computer Science — University of Illinois
  2014 – 2018 · 3.7 GPA

--- SKILLS ---
Python, Go, PostgreSQL, Kubernetes
""".encode()


class _Agent:
    """Builds an agent around a FakeLLM that answers with a given extraction."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.llm = FakeLLM(settings.fixtures_dir)
        probe = ParsingAgent(settings, llm=self.llm, today=TODAY)
        _, sections, rules = probe._prepare(RESUME)
        self.user, self.lines = build_user_message(sections, rules)

    def line(self, prefix: str) -> int:
        """The number the LLM sees for the line starting with `prefix`."""
        return next(n for n, b in self.lines.blocks.items() if b.text.startswith(prefix))

    def extraction(self, **overrides: Any) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "name": "Jane Roe",
            "location": {"city": "Springfield", "region": "IL"},
            "summary_lines": [[self.line("Backend"), self.line("building")]],
            "experience": [
                {
                    "title": "Senior Engineer",
                    "company": "Acme Corp",
                    "location": "Chicago, IL",
                    "dates_text": "Jan 2021 – Present",
                    "bullet_lines": [[self.line("* Built"), self.line("* Led")]],
                },
                {
                    "title": "Engineer",
                    "company": "Globex",
                    "location": "Remote",
                    "dates_text": "06/2018 – 12/2020",
                    "bullet_lines": [[self.line("* Wrote")]],
                },
            ],
            "education": [
                {
                    "institution": "University of Illinois",
                    "degree": "BSc",
                    "field": "Computer Science",
                    "dates_text": "2014 – 2018",
                    "grade": "3.7 GPA",
                }
            ],
            # Skills-section items aren't repeated; a near-duplicate only adds a category.
            "skills": [{"name": "python", "category": "technical"}],
        }
        payload.update(overrides)
        return payload

    def agent(self, payload: dict[str, Any] | None = None, **kwargs: Any) -> ParsingAgent:
        if payload is not None:
            self.llm.register(ResumeExtraction, payload)
        return ParsingAgent(self.settings, llm=self.llm, today=TODAY, **kwargs)


@pytest.fixture
def harness(settings: Settings) -> _Agent:
    return _Agent(settings)


class _RaisingLLM:
    def __init__(self, exc: Exception) -> None:
        self.exc = exc

    async def extract(self, schema: type[T], system: str, user: str) -> T:
        raise self.exc


# -------------------------------------------------------------------------------------------------
# Full parse with the LLM
# -------------------------------------------------------------------------------------------------


async def test_full_parse_merges_rules_and_llm(harness: _Agent) -> None:
    result = await harness.agent(harness.extraction()).parse(RESUME)
    r = result.resume
    assert result.status == "ok"
    assert r.personal.name and r.personal.name.value == "Jane Roe"
    assert r.personal.email and r.personal.email.verified  # from rules
    assert r.personal.phone and r.personal.phone.value == "(415) 555-0134"
    assert r.summary and r.summary.value == (
        "Backend engineer with 6 years of experience building data platforms."
    )

    acme, globex = r.experience
    assert (acme.start and acme.start.value, acme.end, acme.is_current) == ("2021-01", None, True)
    assert acme.duration_months == 69
    assert [b.value for b in acme.responsibilities] == [
        "Built the ingestion pipeline in Python handling 2 TB per day.",
        "Led a team of four.",
    ]
    assert (globex.start and globex.start.value, globex.end and globex.end.value) == (
        "2018-06",
        "2020-12",
    )
    assert globex.duration_months == 30
    edu = r.education[0]
    assert (edu.start and edu.start.value, edu.end and edu.end.value) == ("2014", "2018")

    assert [s.raw for s in r.skills] == ["Python", "Go", "PostgreSQL", "Kubernetes"]
    assert [s.category_hint for s in r.skills] == ["technical", "unknown", "unknown", "unknown"]
    assert acme.skills_mentioned == ["Python"] and globex.skills_mentioned == ["Go"]
    assert r.meta.field_sources["email"] == "rules"
    assert r.meta.field_sources["experience"] == "llm"
    assert r.meta.field_sources["skills"] == "merged"
    assert r.meta.file_type == "txt"
    assert r.meta.sections_found == ["contact", "summary", "experience", "education", "skills"]

    assert r.meta.unverified_count == 0 and r.meta.llm_field_count > 10
    assert all(g.verified for g in iter_grounded(r))
    assert result.quality.score > 0.85
    assert set(result.timings_ms) == {"extract_rules", "llm", "merge_verify"}


async def test_prompt_is_static_and_input_is_numbered(harness: _Agent) -> None:
    system = system_prompt()
    assert "line ranges" in system and "Jane" not in system
    assert "<rule_hints>" in harness.user
    assert "email: jane.roe@example.com" in harness.user
    assert f"{harness.line('* Built')}| * Built the ingestion pipeline" in harness.user
    assert "## section: experience" in harness.user


# -------------------------------------------------------------------------------------------------
# F2: evidence verification (2-C)
# -------------------------------------------------------------------------------------------------


def test_aligner_tolerates_typography_but_not_fabrication() -> None:
    aligner = EvidenceAligner(
        "Senior  Engineer | Acme Corp\nJun 2018 – Oct. 2022\nLed the platform modernization team"
    )
    assert aligner.score("senior engineer | acme corp") == 100
    assert aligner.score("Jun 2018 - Oct. 2022") == 100  # en dash vs hyphen
    assert aligner.score("Led the platfrom modernization team") >= 90  # a typo
    assert aligner.score("Acme Crop") < 90  # one typo in a short span is not enough
    assert aligner.score("Initech Quantum Holdings") < 90
    assert aligner.score("") == 0


async def test_corrupted_extraction_is_flagged_unverified(harness: _Agent) -> None:
    """A deliberately corrupted extraction: a made-up employer and a skill not in the resume."""
    payload = harness.extraction()
    payload["experience"][1]["company"] = "Initech Quantum Holdings"
    payload["skills"].append({"name": "Rust", "category": "technical"})
    result = await harness.agent(payload).parse(RESUME)
    r = result.resume

    company = r.experience[1].company
    assert company is not None and company.verified is False
    assert company.confidence == pytest.approx(0.9 * 0.5)
    rust = next(s for s in r.skills if s.raw == "Rust")
    assert rust.verified is False and rust.confidence == pytest.approx(0.45)
    assert r.experience[0].company and r.experience[0].company.verified is True

    assert r.meta.unverified_count == 2
    assert result.quality.breakdown["unverified_share"] == pytest.approx(
        2 / r.meta.llm_field_count, abs=1e-4
    )
    assert result.status == "ok"  # flagged, not dropped


async def test_pointer_to_missing_line_counts_as_unverified(harness: _Agent) -> None:
    payload = harness.extraction(summary_lines=[[harness.line("Backend")], [999, 1000]])
    result = await harness.agent(payload).parse(RESUME)
    assert result.resume.meta.unverified_count == 1
    assert any("do not exist" in w for w in result.warnings)


def test_verifier_skips_rule_fields_and_counts_extra() -> None:
    resume = ParsedResume.model_validate(
        {
            "personal": {
                "email": {"value": "a@b.co", "evidence": "a@b.co", "verified": True},
                "name": {"value": "Ann Lee", "evidence": "Ann Lee", "confidence": 0.8},
            }
        }
    )
    report = verify_resume(resume, "Ann Lee\na@b.co", extra_unverified=1)
    assert (report.checked, report.unverified) == (2, 1)
    assert resume.personal.name and resume.personal.name.verified is True


# -------------------------------------------------------------------------------------------------
# Merge rules
# -------------------------------------------------------------------------------------------------


def test_rules_win_on_contact_and_llm_fills_gaps() -> None:
    rules = RuleResult(email=Match("jane@x.com", "jane@x.com"))
    extraction = ResumeExtraction(
        name="Jane Roe", email="other@x.com", phone="+1 415 555 0134", links=["janeroe.dev"]
    )
    out = build_resume(rules, [], extraction, harness_lines(), today=TODAY)
    p = out.resume.personal
    assert p.email and p.email.value == "jane@x.com" and p.email.verified
    assert p.phone and p.phone.value == "+1 415 555 0134" and p.phone.verified is None
    assert [link.value for link in p.links] == ["janeroe.dev"]
    sources = out.resume.meta.field_sources
    assert (sources["email"], sources["phone"], sources["name"]) == ("rules", "llm", "llm")


def test_backwards_dates_are_reordered() -> None:
    extraction = ResumeExtraction(
        name="X Y",
        experience=[{"title": "T", "company": "C", "dates_text": "2022 – 2018"}],  # type: ignore[list-item]
    )
    exp = build_resume(RuleResult(), [], extraction, harness_lines(), today=TODAY).resume
    first = exp.experience[0]
    assert (first.start and first.start.value, first.end and first.end.value) == ("2018", "2022")


def test_line_ranges_expand_and_count_invalid() -> None:
    from talentgraph.agents.parsing.layout import Block
    from talentgraph.agents.parsing.llm_extract import NumberedLines

    nl = NumberedLines({n: Block(f"line {n}") for n in range(1, 11)})
    assert nl.valid([[2, 4], [7], [9, 8]]) == ([2, 3, 4, 7, 8, 9], 0)
    assert nl.valid([[5, 40], [], [1, 2, 3], [3, 3]]) == ([3], 3)  # each bad range counts once


def harness_lines() -> Any:
    from talentgraph.agents.parsing.llm_extract import NumberedLines

    return NumberedLines({})


# -------------------------------------------------------------------------------------------------
# Degradation (2-D)
# -------------------------------------------------------------------------------------------------


async def _assert_rules_only(result: Any) -> None:
    r = result.resume
    assert result.status == "partial"
    assert r.personal.email and r.personal.email.value == "jane.roe@example.com"
    assert r.personal.phone and r.personal.phone.value == "(415) 555-0134"
    assert r.personal.name and r.personal.name.value == "Jane Roe"
    assert r.summary is not None
    assert [s.raw for s in r.skills] == ["Python", "Go", "PostgreSQL", "Kubernetes"]
    assert r.experience == [] and r.meta.llm_field_count == 0


async def test_fake_llm_without_fixture_degrades_to_partial(harness: _Agent) -> None:
    result = await harness.agent().parse(RESUME)
    await _assert_rules_only(result)
    assert any("no data" in w for w in result.warnings)


@pytest.mark.parametrize(
    ("exc", "phrase"),
    [(LLMQuotaExceeded("429"), "quota"), (LLMError("boom"), "failed"), (TimeoutError(), "failed")],
)
async def test_llm_failures_degrade_to_partial(
    settings: Settings, exc: Exception, phrase: str
) -> None:
    agent = ParsingAgent(settings, llm=_RaisingLLM(exc), today=TODAY)
    result = await agent.parse(RESUME)
    await _assert_rules_only(result)
    assert any(phrase in w for w in result.warnings)


async def test_nothing_usable_is_failed(settings: Settings) -> None:
    result = await ParsingAgent(settings, llm=FakeLLM(settings.fixtures_dir)).parse(b"?? !!\n")
    assert result.status == "failed"


def test_quality_penalizes_missing_sections() -> None:
    full = ParsedResume.model_validate(
        {
            "personal": {"email": "a@b.co"},
            "experience": [{"title": "T"}],
            "education": [{"institution": "U"}],
            "skills": [{"raw": "Python"}],
        }
    )
    empty = ParsedResume.model_validate({"personal": {"email": "a@b.co"}})
    assert quality_score(full).score == 1.0
    assert quality_score(empty).score == pytest.approx(0.7)
    assert quality_score(empty).breakdown["missing_core_sections"] == 3


# -------------------------------------------------------------------------------------------------
# Errors as HTTP problems (2-E)
# -------------------------------------------------------------------------------------------------


def _scanned_pdf() -> bytes:
    import pymupdf

    doc = pymupdf.open()
    page = doc.new_page()
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 100, 130), False)
    pix.set_rect(pix.irect, (250, 250, 250))
    page.insert_image(page.rect, pixmap=pix)
    return bytes(doc.tobytes())


@pytest.mark.parametrize(
    ("data", "status", "code"),
    [
        (b"\x89PNG\r\n\x1a\n" + b"\x00" * 64, 415, "unsupported_file_type"),
        (b"%PDF-1.7\n" + b"0" * (11 * 1024 * 1024), 413, "file_too_large"),
        (_scanned_pdf(), 422, "unsupported_content"),
    ],
    ids=["png-415", "11mb-413", "scanned-422"],
)
def test_file_errors_render_as_problem_json(
    settings: Settings, data: bytes, status: int, code: str
) -> None:
    agent = ParsingAgent(settings, llm=FakeLLM(settings.fixtures_dir))
    app = FastAPI()
    register_problem_handlers(app)

    @app.post("/parse")
    async def parse(file: UploadFile) -> dict[str, str]:
        result = await agent.parse(await file.read(), file.filename)
        return {"status": result.status}

    response = TestClient(app).post("/parse", files={"file": ("resume.bin", data)})
    assert response.status_code == status
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["type"].endswith(code)


# -------------------------------------------------------------------------------------------------
# Cache (Step 2.12)
# -------------------------------------------------------------------------------------------------


async def test_cache_hit_skips_the_llm(harness: _Agent) -> None:
    cache = InMemoryParseCache()
    agent = harness.agent(harness.extraction(), cache=cache)
    first = await agent.parse(RESUME)
    calls = len(harness.llm.calls)
    second = await agent.parse(RESUME)
    assert not first.cached and second.cached
    assert len(harness.llm.calls) == calls
    assert second.resume == first.resume
    assert cache_key(first.sha256).startswith(f"parse:{first.sha256}:")


async def test_partial_results_are_not_cached(harness: _Agent) -> None:
    cache = InMemoryParseCache()
    agent = harness.agent(cache=cache)  # no extraction registered: partial
    await agent.parse(RESUME)
    assert not (await agent.parse(RESUME)).cached


def test_gold_files_validate_as_parsed_resume() -> None:
    """Step 2.1: every Phase 1 ground-truth profile validates against the v2 schema."""
    profiles = sorted((Path(__file__).resolve().parents[2] / "data" / "profiles").glob("*.json"))
    assert len(profiles) == 560
    for path in profiles:
        resume = ParsedResume.model_validate_json(path.read_text(encoding="utf-8"))
        assert isinstance(resume.personal.name, Extracted)
