"""Step 3.5: Implication rules and ancestor inference (plan §6.2).

Infuses canonical skills with:
1. Implication rules: e.g. {TensorFlow, PyTorch, Keras} >= 1 -> Deep Learning (0.85)
2. Ancestor inference: walks up the 4-level taxonomy (Skill -> Subcategory -> Category -> Domain)
   marking ancestors with `inferred: true`.

Inferred skills carry `inferred: true` and confidence `rule_conf * min(child_conf)`.
Inferred skills NEVER outrank explicit evidence.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from talentgraph.core.schemas.skills import NormalizedSkill

if TYPE_CHECKING:
    from talentgraph.db.repositories.taxonomy import TaxonomyRepository


def infer_hierarchy(
    direct_skills: list[NormalizedSkill],
    repo: TaxonomyRepository,
    include_ancestors: bool = True,
) -> list[NormalizedSkill]:
    """Infer higher-level and implied skills from explicit direct skills."""
    explicit_slugs = {s.slug for s in direct_skills}
    conf_map: dict[str, float] = {s.slug: s.confidence for s in direct_skills}

    inferred_map: dict[str, NormalizedSkill] = {}

    # 1. Implication rules
    triggered_implications = repo.get_implications_for(set(conf_map.keys()))
    for imp in triggered_implications:
        consequent = imp.consequent_slug
        if consequent in explicit_slugs:
            # Explicit evidence always wins; never overwrite explicit skill
            continue

        matching_ants = [a for a in imp.antecedent_slugs if a in conf_map]
        if not matching_ants:
            continue

        min_child_conf = min(conf_map[a] for a in matching_ants)
        conf = round(imp.confidence * min_child_conf, 3)

        # Check if already inferred with higher confidence
        if consequent in inferred_map and inferred_map[consequent].confidence >= conf:
            continue

        sk = repo.get_skill(consequent)
        if not sk:
            continue

        # Category and domain
        cat = None
        if sk.parent_slug:
            parent = repo.get_skill(sk.parent_slug)
            if parent:
                cat = parent.name

        inferred_skill = NormalizedSkill(
            slug=sk.slug,
            name=sk.name,
            level=sk.level,
            category=cat,
            proficiency=2,  # default base proficiency for inferred skills
            years=0.0,
            explanation=f"Inferred via implication rule from {', '.join(matching_ants)}",
            confidence=conf,
            inferred=True,
            raw=[f"implied by {', '.join(matching_ants)}"],
            evidence=[],
            method="inferred",
        )
        inferred_map[consequent] = inferred_skill
        conf_map[consequent] = conf

    # 2. Ancestor hierarchy inference
    if include_ancestors:
        all_active = list(direct_skills) + list(inferred_map.values())
        for skill in all_active:
            ancestors = repo.get_ancestors(skill.slug)
            for anc in ancestors:
                if anc.slug in explicit_slugs:
                    continue

                # Ancestor confidence discount
                anc_conf = round(0.75 * skill.confidence, 3)
                if anc.slug in inferred_map and inferred_map[anc.slug].confidence >= anc_conf:
                    continue

                anc_skill = NormalizedSkill(
                    slug=anc.slug,
                    name=anc.name,
                    level=anc.level,
                    proficiency=skill.proficiency,
                    years=skill.years,
                    explanation=f"Taxonomy ancestor of {skill.name}",
                    confidence=anc_conf,
                    inferred=True,
                    raw=[f"ancestor of {skill.slug}"],
                    evidence=[],
                    method="inferred",
                )
                inferred_map[anc.slug] = anc_skill

    return list(inferred_map.values())
