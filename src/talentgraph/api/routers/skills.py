"""Step 5.4: GET /api/v1/skills/taxonomy, /skills/search, /skills/{id} (plan §8)."""

from typing import Any

from fastapi import APIRouter, Depends, Query
from rapidfuzz import fuzz

from talentgraph.api.deps import get_taxonomy_repo
from talentgraph.api.schemas import SkillDetailResponse, SkillSearchItem
from talentgraph.core.errors import NotFound
from talentgraph.db.repositories.taxonomy import TaxonomyRepository
from talentgraph.embeddings.skill_index import get_skill_index

router = APIRouter(tags=["skills"])


@router.get(
    "/skills/taxonomy",
    response_model=list[dict[str, Any]],
    summary="Browse the taxonomy hierarchy",
)
async def get_taxonomy_tree(
    parent_id: int | None = Query(None, description="Parent skill ID (None for root domains)"),
    depth: int = Query(1, ge=1, le=4, description="Depth of hierarchy to fetch"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    repo: TaxonomyRepository = Depends(get_taxonomy_repo),
) -> list[dict[str, Any]]:
    """Browse skills from the taxonomy tree by parent ID or root domains."""
    if parent_id is None:
        # Return level 0 roots (domains)
        nodes = [s for s in repo.skills if s.level == 0]
    else:
        parent_skill = repo.get_skill_by_id(parent_id)
        if parent_skill is None:
            raise NotFound(f"Parent skill {parent_id} not found")
        nodes = repo.get_children(parent_skill.slug)

    paginated = nodes[offset : offset + limit]
    results: list[dict[str, Any]] = []
    for node in paginated:
        results.append(
            {
                "id": node.id,
                "slug": node.slug,
                "name": node.name,
                "type": node.type,
                "level": node.level,
                "parent_slug": node.parent_slug,
                "has_children": len(repo.get_children(node.slug)) > 0,
            }
        )

    return results


@router.get(
    "/skills/search",
    response_model=list[SkillSearchItem],
    summary="Search skills by keyword or semantic query",
)
async def search_skills(
    q: str = Query(..., min_length=1, description="Search query string"),
    limit: int = Query(20, ge=1, le=100),
    repo: TaxonomyRepository = Depends(get_taxonomy_repo),
) -> list[SkillSearchItem]:
    """Search skills across alias exact match, fuzzy matching, and embeddings."""
    q_norm = q.strip().lower()
    hits: dict[str, SkillSearchItem] = {}

    # 1. Exact alias match
    alias_rec = repo.resolve_alias(q_norm)
    if alias_rec:
        sk = repo.get_skill(alias_rec.canonical_slug)
        if sk:
            hits[sk.slug] = SkillSearchItem(
                slug=sk.slug,
                name=sk.name,
                score=1.0,
                match_type="exact",
                type=sk.type,
            )

    # 2. Fuzzy matching against skill names and aliases
    for s in repo.skills:
        if s.slug in hits:
            continue
        ratio = fuzz.token_sort_ratio(q_norm, s.name.lower()) / 100.0
        if ratio >= 0.70:
            hits[s.slug] = SkillSearchItem(
                slug=s.slug,
                name=s.name,
                score=ratio,
                match_type="fuzzy",
                type=s.type,
            )

    # 3. Embedding search fallback
    try:
        skill_idx = get_skill_index()
        vec_hits = skill_idx.query(q, top_k=limit)
        for slug, sim in vec_hits:
            if slug not in hits:
                sk = repo.get_skill(slug)
                if sk:
                    hits[slug] = SkillSearchItem(
                        slug=sk.slug,
                        name=sk.name,
                        score=float(sim),
                        match_type="vector",
                        type=sk.type,
                    )
    except Exception:
        pass

    results = sorted(hits.values(), key=lambda h: h.score, reverse=True)
    return results[:limit]


@router.get(
    "/skills/{skill_id_or_slug}",
    response_model=SkillDetailResponse,
    summary="Get skill details by ID or slug",
)
async def get_skill_detail(
    skill_id_or_slug: str,
    repo: TaxonomyRepository = Depends(get_taxonomy_repo),
) -> SkillDetailResponse:
    """Retrieve skill information with full ancestor path, children, aliases, and relations."""
    skill = None
    if skill_id_or_slug.isdigit():
        skill = repo.get_skill_by_id(int(skill_id_or_slug))
    if skill is None:
        skill = repo.get_skill(skill_id_or_slug)

    if skill is None:
        raise NotFound(f"Skill '{skill_id_or_slug}' not found")

    ancestors = [
        {"id": a.id, "slug": a.slug, "name": a.name, "level": a.level}
        for a in repo.get_ancestors(skill.slug)
    ]
    children = [
        {"id": c.id, "slug": c.slug, "name": c.name, "level": c.level}
        for c in repo.get_children(skill.slug)
    ]
    aliases = [a.alias for a in repo.aliases if a.canonical_slug == skill.slug]
    related = [
        {"target_slug": r.related_slug, "kind": r.kind, "weight": r.weight}
        for r in repo.get_relations(skill.slug)
    ]

    return SkillDetailResponse(
        id=skill.id,
        slug=skill.slug,
        name=skill.name,
        type=skill.type,
        level=skill.level,
        description=skill.description,
        ancestors=ancestors,
        children=children,
        aliases=aliases,
        related=related,
    )
