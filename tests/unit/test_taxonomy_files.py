"""Exit criteria 1-B and 1-D: taxonomy file integrity and required alias resolutions."""

from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any

import pytest
import yaml

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "taxonomy"


def normalize_alias(text: str) -> str:
    """Same normalization as scripts/build_taxonomy.normalize_alias_text."""
    return re.sub(r"[\s\-_/.]+", " ", text.lower().strip()).strip()


@pytest.fixture(scope="module")
def taxonomy_data() -> dict[str, Any]:
    with open(DATA_DIR / "skills.csv", encoding="utf-8") as f:
        skills = list(csv.DictReader(f))
    with open(DATA_DIR / "aliases.csv", encoding="utf-8") as f:
        aliases = list(csv.DictReader(f))
    with open(DATA_DIR / "implications.yaml", encoding="utf-8") as f:
        implications = yaml.safe_load(f).get("implications", [])
    with open(DATA_DIR / "relations.yaml", encoding="utf-8") as f:
        relations = yaml.safe_load(f).get("relations", [])
    return {
        "skills": skills,
        "aliases": aliases,
        "implications": implications,
        "relations": relations,
    }


def test_taxonomy_size_and_levels(taxonomy_data: dict[str, Any]) -> None:
    skills = taxonomy_data["skills"]
    assert len(skills) >= 5000, f"Expected >= 5000 skills, found {len(skills)}"
    assert len(taxonomy_data["aliases"]) >= 15000
    assert {int(s["level"]) for s in skills} == {0, 1, 2, 3}
    assert sum(int(s["level"]) == 0 for s in skills) == 4


def test_no_placeholder_skills(taxonomy_data: dict[str, Any]) -> None:
    """Regression guard: the taxonomy once padded its counts with 'X Spec NNN' filler."""
    filler = [s["slug"] for s in taxonomy_data["skills"] if re.search(r"-spec-\d+$", s["slug"])]
    assert not filler, f"placeholder skills found: {filler[:5]}"


def test_unique_slugs_and_normalized_aliases(taxonomy_data: dict[str, Any]) -> None:
    slugs = [s["slug"] for s in taxonomy_data["skills"]]
    assert len(slugs) == len(set(slugs)), "Duplicate skill slugs found"

    normalized = [a["alias_normalized"] for a in taxonomy_data["aliases"]]
    assert len(normalized) == len(set(normalized)), "Duplicate normalized aliases found"
    bad = [
        a for a in taxonomy_data["aliases"] if a["alias_normalized"] != normalize_alias(a["alias"])
    ]
    assert not bad, f"alias_normalized does not match the normalizer: {bad[:3]}"


def test_aliases_reference_existing_skills(taxonomy_data: dict[str, Any]) -> None:
    slugs = {s["slug"] for s in taxonomy_data["skills"]}
    dangling = [a for a in taxonomy_data["aliases"] if a["slug"] not in slugs]
    assert not dangling, f"aliases pointing at missing skills: {dangling[:3]}"


def test_hierarchy_integrity_and_no_cycles(taxonomy_data: dict[str, Any]) -> None:
    slug_map = {s["slug"]: s for s in taxonomy_data["skills"]}
    for s in taxonomy_data["skills"]:
        level = int(s["level"])
        if level == 0:
            assert not s["parent_slug"], f"Root domain {s['slug']} should not have a parent"
            continue
        assert s["parent_slug"] in slug_map, f"{s['slug']} has missing parent {s['parent_slug']}"
        assert int(slug_map[s["parent_slug"]]["level"]) == level - 1

    for s in taxonomy_data["skills"]:
        visited: set[str] = set()
        curr = s["slug"]
        while curr and curr in slug_map:
            assert curr not in visited, f"Cycle detected in taxonomy at slug: {curr}"
            visited.add(curr)
            curr = slug_map[curr]["parent_slug"]


def test_implications_and_relations_reference_existing_slugs(
    taxonomy_data: dict[str, Any],
) -> None:
    slugs = {s["slug"] for s in taxonomy_data["skills"]}

    implications = taxonomy_data["implications"]
    assert len(implications) >= 150
    for imp in implications:
        assert imp["consequent_slug"] in slugs, imp
        for antecedent in imp["antecedent_slugs"]:
            assert antecedent in slugs, imp

    relations = taxonomy_data["relations"]
    assert len(relations) >= 300
    for rel in relations:
        assert rel["skill_slug"] in slugs, rel
        assert rel["related_slug"] in slugs, rel
        assert rel["kind"] in ("related", "prerequisite"), rel


@pytest.mark.parametrize(
    "word", ["go", "r", "c", "spring", "swift", "rust", "excel", "word", "access", "pm", "cv"]
)
def test_ambiguous_aliases_flagged(taxonomy_data: dict[str, Any], word: str) -> None:
    by_norm = {a["alias_normalized"]: a for a in taxonomy_data["aliases"]}
    assert word in by_norm, f"ambiguous alias {word!r} missing from aliases.csv"
    assert by_norm[word]["ambiguous"] == "true", f"{word!r} must be flagged ambiguous"


@pytest.mark.parametrize(
    ("surface", "expected"),
    [
        ("js", "javascript"),
        ("k8s", "kubernetes"),
        ("react.js", "react"),
        ("ReactJS", "react"),
        ("ML Engineering", "machine-learning-engineering"),
        ("ts", "typescript"),
        ("tf", "tensorflow"),
        ("gcp", "google-cloud-platform"),
        ("aws", "amazon-web-services"),
        ("MS Excel", "microsoft-excel"),
    ],
)
def test_required_exact_alias_resolutions(
    taxonomy_data: dict[str, Any], surface: str, expected: str
) -> None:
    alias_to_slug = {a["alias_normalized"]: a["slug"] for a in taxonomy_data["aliases"]}
    norm = normalize_alias(surface)
    assert alias_to_slug.get(norm) == expected, f"{surface!r} -> {alias_to_slug.get(norm)!r}"
