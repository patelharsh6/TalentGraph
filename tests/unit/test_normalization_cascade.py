"""Unit tests for Step 3.4: Normalization cascade."""

import pytest

from talentgraph.agents.normalization.cascade import SkillCascade
from talentgraph.db.repositories.taxonomy import get_taxonomy_repository
from talentgraph.embeddings.skill_index import get_skill_index


@pytest.fixture(scope="module")
def cascade() -> SkillCascade:
    repo = get_taxonomy_repository()
    index = get_skill_index()
    return SkillCascade(repo=repo, skill_index=index)


def test_cascade_exact_alias(cascade: SkillCascade) -> None:
    res = cascade.normalize_one_sync("k8s")
    assert len(res) == 1
    assert res[0].canonical is not None
    assert res[0].canonical.slug == "kubernetes"
    assert res[0].method == "exact"
    assert res[0].confidence == 1.0


def test_cascade_version(cascade: SkillCascade) -> None:
    res = cascade.normalize_one_sync("Python 3.11")
    assert len(res) == 1
    assert res[0].canonical is not None
    assert res[0].canonical.slug == "python"
    assert res[0].method == "exact"


def test_cascade_multi_skill(cascade: SkillCascade) -> None:
    res = cascade.normalize_one_sync("Python/Django")
    assert len(res) == 2
    slugs = [r.canonical.slug for r in res if r.canonical]
    assert "python" in slugs
    assert "django" in slugs


def test_cascade_fuzzy_typo(cascade: SkillCascade) -> None:
    res = cascade.normalize_one_sync("Adobee XD")
    assert len(res) == 1
    assert res[0].canonical is not None
    assert res[0].canonical.slug == "adobe-xd"
    assert res[0].method == "fuzzy"
    assert res[0].confidence >= 0.90


def test_cascade_ambiguous_with_context(cascade: SkillCascade) -> None:
    # Context 1: Golang
    res1 = cascade.normalize_one_sync(
        "Go", context="Engineered high-throughput concurrent microservices in Go using goroutines."
    )
    assert len(res1) == 1
    assert res1[0].canonical is not None
    assert res1[0].canonical.slug == "golang"

    # Context 2: Go-to-market
    res2 = cascade.normalize_one_sync(
        "Go", context="Led the go-to-market launch for our enterprise analytics product."
    )
    assert len(res2) == 1
    assert res2[0].canonical is not None
    assert res2[0].canonical.slug == "go-to-market-strategy"


def test_cascade_unrecognized(cascade: SkillCascade) -> None:
    res = cascade.normalize_one_sync("Mamba state-space models")
    assert len(res) == 1
    assert res[0].canonical is None
    assert res[0].method == "unrecognized"
    assert res[0].unrecognized is not None
    assert "mamba" in res[0].unrecognized.normalized
