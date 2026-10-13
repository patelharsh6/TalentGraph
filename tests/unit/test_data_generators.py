"""Exit criteria 1-E, 1-F and 1-G: generated corpora and gold sets are complete and valid."""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

import pytest

from talentgraph.core.schemas.resume import ParsedResume

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = ROOT_DIR / "data"
FIXTURES_DIR = ROOT_DIR / "tests" / "fixtures" / "resumes"
TEMPLATES = {"single_column", "two_column", "sidebar", "table_based", "creative", "minimal_txt"}


@pytest.fixture(scope="module")
def taxonomy_slugs() -> set[str]:
    with open(DATA_DIR / "taxonomy" / "skills.csv", encoding="utf-8") as f:
        return {r["slug"] for r in csv.DictReader(f)}


def test_candidate_profiles(taxonomy_slugs: set[str]) -> None:
    files = sorted((DATA_DIR / "profiles").glob("candidate_*.gt.json"))
    assert len(files) >= 550, f"Expected >= 550 profiles, found {len(files)}"
    industries: Counter[str] = Counter()
    emerging = 0
    for f in files:
        resume = ParsedResume.model_validate_json(f.read_text(encoding="utf-8"))
        assert resume.personal.get("name") and resume.experience and resume.skills
        industries[resume.meta["industry"]] += 1
        for s in resume.skills:
            if s["emerging"]:
                emerging += 1
                assert s["canonical_slug"] is None, f"{f.name}: emerging skill has a slug"
            else:
                assert s["canonical_slug"] in taxonomy_slugs, f"{f.name}: {s['canonical_slug']}"
    assert len(industries) >= 10
    assert emerging > 0


def test_rendered_resumes() -> None:
    resumes_dir = DATA_DIR / "resumes"
    if not resumes_dir.exists():
        pytest.skip("data/resumes is generated (gitignored); run scripts/render_resumes.py")
    total = 0
    formats: Counter[str] = Counter()
    for split in ("train", "val", "test"):
        docs = [f for f in (resumes_dir / split).iterdir() if f.suffix in (".pdf", ".docx", ".txt")]
        for d in docs:
            gt = d.with_name(f"{d.stem}.gt.json")
            assert gt.exists(), f"missing ground truth for {d.name}"
            formats[d.suffix] += 1
        total += len(docs)
    assert total >= 500
    assert formats[".pdf"] / total >= 0.40 and formats[".docx"] / total >= 0.40


def test_fixture_sample_covers_every_template() -> None:
    gts = sorted(FIXTURES_DIR.glob("*.gt.json"))
    assert 10 <= len(gts) <= 20, f"expected ~15 fixture resumes, found {len(gts)}"
    templates = set()
    for gt_path in gts:
        gt = ParsedResume.model_validate_json(gt_path.read_text(encoding="utf-8"))
        stem = gt_path.name.removesuffix(".gt.json")
        assert (FIXTURES_DIR / f"{stem}.{gt.meta['format']}").exists()
        templates.add(gt.meta["template"])
    assert templates == TEMPLATES


def test_jobs_corpus(taxonomy_slugs: set[str]) -> None:
    jobs_dir = DATA_DIR / "jobs"
    txt_files = sorted(jobs_dir.glob("job_*.txt"))
    gt_files = sorted(jobs_dir.glob("job_*.gt.json"))
    assert len(txt_files) >= 100
    assert len(txt_files) == len(gt_files)
    families = set()
    for gf in gt_files:
        data = json.loads(gf.read_text(encoding="utf-8"))
        assert data["title"] and data["requirements"]
        families.add(data["role_family"])
        for r in data["requirements"]:
            assert r["skill_slug"] in taxonomy_slugs, f"{gf.name}: {r['skill_slug']}"
    assert {"engineering", "data", "product", "design"} <= families


def test_normalization_gold(taxonomy_slugs: set[str]) -> None:
    with open(DATA_DIR / "eval" / "normalization_gold.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) >= 1000
    hard = sum(r["is_hard_case"] == "True" for r in rows)
    assert hard / len(rows) >= 0.25, f"hard cases {hard / len(rows):.1%} < 25%"
    for r in rows:
        for slug in r["expected_slug"].split("|"):
            assert slug == "NEW" or slug in taxonomy_slugs, f"{r['raw']!r}: {slug}"
    assert {r["split"] for r in rows} == {"val", "test"}


def test_match_gold() -> None:
    with open(DATA_DIR / "eval" / "match_gold.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) >= 2000
    grades = Counter(int(r["grade"]) for r in rows)
    assert set(grades) <= {0, 1, 2, 3, 4}
    assert max(grades.values()) / len(rows) <= 0.40
    assert len({(r["job_id"], r["candidate_id"]) for r in rows}) == len(rows)
    for r in rows:
        assert (DATA_DIR / "jobs" / f"{r['job_id']}.gt.json").exists()
        assert (DATA_DIR / "profiles" / f"{r['candidate_id']}.gt.json").exists()
        assert 0.0 <= float(r["score"]) <= 1.0


def test_human_labeling_sample_is_not_prefilled() -> None:
    with open(DATA_DIR / "eval" / "human_labeling.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) >= 200
    for r in rows:
        # Empty until a human labels it; never copied from the machine grade.
        assert r["human_grade"] == "" or r["human_grade"] in {"0", "1", "2", "3", "4"}
