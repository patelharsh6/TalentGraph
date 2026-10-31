"""Unit tests for Step 3.2: Raw skill cleaning."""

from talentgraph.agents.normalization.clean import (
    clean_raw_skill,
    split_multi_skills,
    strip_version,
)
from talentgraph.db.repositories.taxonomy import get_taxonomy_repository


def test_strip_version() -> None:
    assert strip_version("Python 3.11") == "Python"
    assert strip_version("Java 17") == "Java"
    assert strip_version("Java SE 21") == "Java"
    assert strip_version("C++20") == "C++"
    assert strip_version("Vue.js v3.2") == "Vue.js"
    assert strip_version("Node.js 20 LTS") == "Node.js"
    assert strip_version("Figma (2024)") == "Figma"

    # Known aliases with numbers should NOT have their numbers stripped
    assert strip_version("HTML5") == "HTML5"
    assert strip_version("CSS3") == "CSS3"


def test_split_multi_skills() -> None:
    repo = get_taxonomy_repository()

    assert split_multi_skills("Python/Django", repo) == ["Python", "Django"]
    assert split_multi_skills("Python & FastAPI", repo) == ["Python", "FastAPI"]
    assert split_multi_skills("React + TypeScript", repo) == ["React", "TypeScript"]
    assert split_multi_skills("HTML/CSS/JavaScript", repo) == ["HTML", "CSS", "JavaScript"]
    assert split_multi_skills("Pandas, NumPy", repo) == ["Pandas", "NumPy"]
    assert split_multi_skills("C++ / C#", repo) == ["C++", "C#"]

    # Known composite aliases should not be split
    assert split_multi_skills("HL7 / FHIR", repo) == ["HL7 / FHIR"]


def test_clean_raw_skill_end_to_end() -> None:
    repo = get_taxonomy_repository()

    # Bullet stripping and version stripping
    res = clean_raw_skill("• Python 3.10", repo)
    assert res == ["Python"]

    # Multi-skill + versions
    res2 = clean_raw_skill("Docker 24 & Kubernetes 1.29", repo)
    assert res2 == ["Docker", "Kubernetes"]
