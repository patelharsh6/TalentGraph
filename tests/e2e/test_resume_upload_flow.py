"""Regression tests for the resume upload -> parse -> profile flow end-to-end.

Tests:
1. Single-column PDF (candidate_0016.pdf)
2. Two-column / multi-column PDF (candidate_0018.pdf)
3. DOCX with tables (candidate_0022.docx)
4. Plain TXT (candidate_0009.txt)
5. Scanned / empty PDF (zero text layer -> UnsupportedContent)
6. Error cases: .exe binary (415), empty file (415), oversized file (413), corrupt PDF (422)
7. Pure heuristic fallback when LLM is unavailable or quota exhausted (429)
"""

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pymupdf
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from talentgraph.agents.matching.agent import MatchingAgent
from talentgraph.agents.matching.job_parser import JobParser
from talentgraph.agents.normalization.agent import NormalizationAgent
from talentgraph.agents.parsing.agent import ParsingAgent
from talentgraph.agents.parsing.cache import InMemoryParseCache
from talentgraph.api.main import create_app
from talentgraph.config import Settings
from talentgraph.core.errors import LLMQuotaExceeded
from talentgraph.db.in_memory import clear_in_memory_db
from talentgraph.db.repositories.taxonomy import get_taxonomy_repository
from talentgraph.llm.fake import FakeLLM


class _RaisingLLM:
    def __init__(self, exc: Exception) -> None:
        self.exc = exc

    async def extract(self, *args: Any, **kwargs: Any) -> Any:
        raise self.exc


pytestmark = [pytest.mark.unit]

ROOT = Path(__file__).resolve().parents[2]
FIXTURES_DIR = ROOT / "tests" / "fixtures"
RESUMES_DIR = FIXTURES_DIR / "resumes"


@pytest.fixture(autouse=True)
def _reset_in_memory_db() -> Iterator[None]:
    clear_in_memory_db()
    yield
    clear_in_memory_db()


@pytest.fixture
def app() -> FastAPI:
    """FastAPI test app configured for offline execution."""
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


def test_resume_type_1_single_column_pdf(client: TestClient) -> None:
    """1. Test upload & parse for a single-column PDF resume."""
    pdf_path = RESUMES_DIR / "candidate_0016.pdf"
    assert pdf_path.exists(), f"Fixture missing: {pdf_path}"

    with open(pdf_path, "rb") as f:
        res = client.post(
            "/api/v1/parse", files={"file": ("candidate_0016.pdf", f, "application/pdf")}
        )

    assert res.status_code == 200
    body = res.json()
    data = body["data"]

    # Verify structured fields
    cand_id = data["candidate_id"]
    parsed = data["parsed"]
    personal = parsed["personal"]

    assert personal["name"]["value"] == "Jack Snow"
    assert "jack.snow" in personal["email"]["value"]
    assert len(parsed["experience"]) >= 1
    assert parsed["experience"][0]["title"]["value"] is not None
    assert len(parsed["education"]) >= 1
    assert len(data["profile"]["skills"]) >= 3

    # Verify profile is retrievable by candidate_id
    detail_res = client.get(f"/api/v1/candidates/{cand_id}")
    assert detail_res.status_code == 200
    assert detail_res.json()["id"] == cand_id


def test_resume_type_2_two_column_pdf(client: TestClient) -> None:
    """2. Test upload & parse for a two-column / multi-column PDF resume."""
    pdf_path = RESUMES_DIR / "candidate_0018.pdf"
    assert pdf_path.exists(), f"Fixture missing: {pdf_path}"

    with open(pdf_path, "rb") as f:
        res = client.post(
            "/api/v1/parse", files={"file": ("candidate_0018.pdf", f, "application/pdf")}
        )

    assert res.status_code == 200
    body = res.json()
    data = body["data"]

    parsed = data["parsed"]
    assert parsed["personal"]["name"]["value"] == "Emily Newton"
    assert "emily.newton" in parsed["personal"]["email"]["value"]
    assert len(parsed["experience"]) >= 1
    assert len(data["profile"]["skills"]) >= 3


def test_resume_type_3_docx_with_tables(client: TestClient) -> None:
    """3. Test upload & parse for a DOCX resume containing structured tables."""
    docx_path = RESUMES_DIR / "candidate_0022.docx"
    assert docx_path.exists(), f"Fixture missing: {docx_path}"

    with open(docx_path, "rb") as f:
        res = client.post(
            "/api/v1/parse",
            files={
                "file": (
                    "candidate_0022.docx",
                    f,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )

    assert res.status_code == 200
    body = res.json()
    data = body["data"]

    parsed = data["parsed"]
    assert parsed["personal"]["name"]["value"] == "Olivia Harris"
    assert "olivia.harris" in parsed["personal"]["email"]["value"]
    assert len(parsed["experience"]) >= 1
    assert len(data["profile"]["skills"]) >= 3


def test_resume_type_4_plain_text(client: TestClient) -> None:
    """4. Test upload & parse for a plain TXT resume."""
    txt_path = RESUMES_DIR / "candidate_0009.txt"
    assert txt_path.exists(), f"Fixture missing: {txt_path}"

    with open(txt_path, "rb") as f:
        res = client.post("/api/v1/parse", files={"file": ("candidate_0009.txt", f, "text/plain")})

    assert res.status_code == 200
    body = res.json()
    data = body["data"]

    parsed = data["parsed"]
    assert parsed["personal"]["name"]["value"] is not None
    assert "steven.flynn" in parsed["personal"]["email"]["value"]
    assert len(parsed["experience"]) >= 1
    assert len(data["profile"]["skills"]) >= 3


def test_resume_type_5_scanned_or_empty_pdf_rejected(client: TestClient) -> None:
    """5. Test that a scanned/empty PDF (no text layer) produces a clear 422 error."""
    # Create empty PDF in memory
    doc = pymupdf.open()
    doc.new_page()  # 1 blank page without text
    empty_pdf_bytes = doc.tobytes()
    doc.close()

    res = client.post(
        "/api/v1/parse",
        files={"file": ("scanned_resume.pdf", empty_pdf_bytes, "application/pdf")},
    )

    assert res.status_code == 422
    body = res.json()
    assert body["status"] == 422
    assert "scanned" in body["detail"].lower() or "text layer" in body["detail"].lower()


def test_error_path_windows_executable(client: TestClient) -> None:
    """Test that a .exe binary is rejected with a clear 415 error."""
    fake_exe_bytes = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00"
    res = client.post(
        "/api/v1/parse",
        files={"file": ("malware.exe", fake_exe_bytes, "application/x-msdownload")},
    )
    assert res.status_code == 415
    body = res.json()
    assert "executable" in body["detail"].lower() or "unsupported" in body["title"].lower()


def test_error_path_empty_file(client: TestClient) -> None:
    """Test that an empty 0-byte file is rejected with 415."""
    res = client.post(
        "/api/v1/parse",
        files={"file": ("empty.pdf", b"", "application/pdf")},
    )
    assert res.status_code == 415
    body = res.json()
    assert "empty" in body["detail"].lower()


def test_error_path_corrupted_pdf(client: TestClient) -> None:
    """Test that corrupted PDF bytes return 422 with readable error message."""
    corrupt_bytes = b"%PDF-1.4\ncorrupted binary contents that are invalid garbage"
    res = client.post(
        "/api/v1/parse",
        files={"file": ("corrupt.pdf", corrupt_bytes, "application/pdf")},
    )
    assert res.status_code == 422
    body = res.json()
    assert "corrupt" in body["detail"].lower()


def test_error_path_oversized_file(client: TestClient) -> None:
    """Test that a file exceeding 10 MB limit is rejected with 413."""
    oversized_bytes = b"%PDF-1.4\n" + (b"0" * (11 * 1024 * 1024))
    res = client.post(
        "/api/v1/parse",
        files={"file": ("huge_resume.pdf", oversized_bytes, "application/pdf")},
    )
    assert res.status_code == 413
    body = res.json()
    assert "limit" in body["detail"].lower() or "file too large" in body["title"].lower()


def test_heuristic_fallback_when_llm_fails(app: FastAPI, client: TestClient) -> None:
    """Test that pure heuristic fallback produces rich, populated fields without crashing."""
    # Configure ParsingAgent with a raising LLM to simulate 429 quota exhaustion
    test_settings = Settings(
        app_env="test",
        api_key=None,
        llm_mode="real",
    )
    app.state.parsing_agent = ParsingAgent(
        settings=test_settings,
        llm=_RaisingLLM(LLMQuotaExceeded("429 Resource has been exhausted")),
        cache=InMemoryParseCache(),
    )

    pdf_path = RESUMES_DIR / "candidate_0016.pdf"
    with open(pdf_path, "rb") as f:
        res = client.post(
            "/api/v1/parse", files={"file": ("candidate_0016.pdf", f, "application/pdf")}
        )

    assert res.status_code == 200
    body = res.json()
    data = body["data"]

    # Verify status is partial (rules-only degradation)
    assert data["status"] == "partial"

    # Verify all core fields are populated by heuristic rules
    parsed = data["parsed"]
    assert parsed["personal"]["name"]["value"] == "Jack Snow"
    assert "jack.snow" in parsed["personal"]["email"]["value"]
    assert len(parsed["experience"]) >= 1
    assert parsed["experience"][0]["title"]["value"] is not None
    assert len(parsed["education"]) >= 1
    assert len(data["profile"]["skills"]) >= 3
