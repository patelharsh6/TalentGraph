"""Unit tests for Step 3.3: SkillIndex helper."""

from talentgraph.embeddings.skill_index import get_skill_index


def test_skill_index_offline_query() -> None:
    index = get_skill_index()
    assert index.count() >= 5000

    hits = index.query("container orchestration tool", k=5)
    assert len(hits) == 5
    slugs = [h.id for h in hits]
    assert any(s in slugs for s in ("container-orchestration", "kubernetes", "docker"))
    assert hits[0].score > 0.6
