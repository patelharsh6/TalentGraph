"""Unit tests for Step 3.1: SkillProfile schema and TaxonomyRepository."""

from talentgraph.core.schemas.skills import (
    EmergingSkillMention,
    NormalizedSkill,
    SkillProfile,
)
from talentgraph.db.repositories.taxonomy import (
    TaxonomyRepository,
    get_taxonomy_repository,
    normalize_alias_text,
)


def test_skill_profile_schema() -> None:
    skill = NormalizedSkill(
        slug="kubernetes",
        name="Kubernetes",
        category="DevOps",
        proficiency=4,
        years=5.5,
        explanation="5.5 years across 2 roles",
        confidence=1.0,
        raw=["k8s", "Kubernetes"],
        evidence=["Led migration to K8s"],
        method="exact",
    )
    unrec = EmergingSkillMention(
        raw="SomeObscureTool",
        normalized="someobscuretool",
        context="Built pipelines with SomeObscureTool",
    )
    profile = SkillProfile(
        skills=[skill],
        unrecognized=[unrec],
    )

    assert len(profile.skills) == 1
    assert profile.get("kubernetes") is not None
    assert profile.get("python") is None
    assert len(profile.direct_skills) == 1
    assert len(profile.inferred_skills) == 0
    assert len(profile.unrecognized) == 1
    assert profile.unrecognized[0].normalized == "someobscuretool"


def test_taxonomy_repository_loading() -> None:
    repo = get_taxonomy_repository()
    assert len(repo.skills) >= 5000
    assert len(repo.aliases) >= 15000
    assert len(repo.implications) >= 150
    assert len(repo.relations) >= 300

    # Required resolutions
    assert repo.resolve_alias("js") is not None
    assert repo.resolve_alias("js").slug == "javascript"  # type: ignore[union-attr]
    assert repo.resolve_alias("k8s").slug == "kubernetes"  # type: ignore[union-attr]
    assert repo.resolve_alias("ReactJS").slug == "react"  # type: ignore[union-attr]
    assert repo.resolve_alias("ML Engineering").slug == "machine-learning-engineering"  # type: ignore[union-attr]

    # Skill lookup
    py = repo.get_skill("python")
    assert py is not None
    assert py.name == "Python"
    assert py.level == 3

    # Ancestor chain
    ancestors = repo.get_ancestors("python")
    assert len(ancestors) == 3
    # Subcategory -> Category -> Domain (level 0)
    assert ancestors[-1].level == 0


def test_taxonomy_implications() -> None:
    repo = get_taxonomy_repository()
    # Check trigger for Deep Learning or similar
    triggered = repo.get_implications_for({"tensorflow", "pytorch"})
    assert any(imp.consequent_slug == "deep-learning" for imp in triggered)

