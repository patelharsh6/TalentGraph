"""Unit tests for Step 3.5: Hierarchy and implication rules (Exit Criterion 3-C)."""

from talentgraph.agents.normalization.hierarchy import infer_hierarchy
from talentgraph.core.schemas.skills import NormalizedSkill
from talentgraph.db.repositories.taxonomy import get_taxonomy_repository


def test_tensorflow_pytorch_implies_deep_learning() -> None:
    repo = get_taxonomy_repository()

    tf = NormalizedSkill(
        slug="tensorflow",
        name="TensorFlow",
        level=3,
        confidence=1.0,
        inferred=False,
    )
    pytorch = NormalizedSkill(
        slug="pytorch",
        name="PyTorch",
        level=3,
        confidence=0.9,
        inferred=False,
    )

    inferred = infer_hierarchy([tf, pytorch], repo=repo, include_ancestors=False)
    slugs = {s.slug: s for s in inferred}

    assert "deep-learning" in slugs
    dl = slugs["deep-learning"]
    assert dl.inferred is True
    # Confidence: 0.85 * min(1.0, 0.9) = 0.765
    assert dl.confidence == 0.765
    assert dl.method == "inferred"


def test_inferred_skills_never_outrank_explicit() -> None:
    repo = get_taxonomy_repository()

    tf = NormalizedSkill(
        slug="tensorflow",
        name="TensorFlow",
        level=3,
        confidence=1.0,
        inferred=False,
    )
    # Explicit deep learning
    dl_explicit = NormalizedSkill(
        slug="deep-learning",
        name="Deep Learning",
        level=2,
        confidence=1.0,
        inferred=False,
    )

    inferred = infer_hierarchy([tf, dl_explicit], repo=repo, include_ancestors=True)
    slugs = {s.slug for s in inferred}

    # deep-learning should NOT be in inferred list because it was explicit
    assert "deep-learning" not in slugs


def test_ancestor_inference() -> None:
    repo = get_taxonomy_repository()

    py = NormalizedSkill(
        slug="python",
        name="Python",
        level=3,
        confidence=1.0,
        inferred=False,
    )

    inferred = infer_hierarchy([py], repo=repo, include_ancestors=True)
    slug_map = {s.slug: s for s in inferred}

    # Python's ancestors in the 4-level taxonomy
    ancestors = repo.get_ancestors("python")
    for anc in ancestors:
        assert anc.slug in slug_map
        assert slug_map[anc.slug].inferred is True
