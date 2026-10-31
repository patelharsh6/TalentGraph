"""Step 4.4: gap analysis and upskilling hints (plan §6.3).

Identifies unmet requirements, current vs required proficiency, and surfaces
adjacent skills via taxonomy `related` and sibling edges.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from talentgraph.core.schemas.matching import GapItem, JobRequirement, RequirementCredit
from talentgraph.core.schemas.skills import SkillProfile
from talentgraph.db.repositories.taxonomy import TaxonomyRepository

if TYPE_CHECKING:
    pass


def format_required_proficiency(req: JobRequirement) -> str:
    """Format expected proficiency description based on required years and importance."""
    if req.min_years is not None and req.min_years > 0:
        return f"Level {min(5, int(req.min_years) + 1)} ({req.min_years:.0f}+ yrs required)"
    if req.importance >= 4:
        return "Level 4 (Advanced/Proficient)"
    return "Level 3 (Competent)"


def format_current_proficiency(credit: RequirementCredit, profile: SkillProfile) -> str:
    """Format candidate current proficiency level for a matched/partially matched requirement."""
    if not credit.matched_slug or credit.credit == 0.0:
        return "None (0.0 yrs)"
    matched_skill = profile.get(credit.matched_slug)
    if matched_skill is not None:
        return f"Level {matched_skill.proficiency} ({matched_skill.years:.1f} yrs via {matched_skill.name})"
    return f"Partial ({credit.credit:.1%})"


def generate_upskilling_hints(
    gap_slug: str,
    gap_name: str,
    profile: SkillProfile,
    repo: TaxonomyRepository | None,
    max_hints: int = 3,
) -> list[str]:
    """Find skills the candidate already possesses that bridge to the gap skill."""
    if repo is None:
        return []

    hints: list[str] = []
    gap_skill = repo.get_skill(gap_slug)
    if gap_skill is None:
        return hints

    cand_slugs = {s.slug: s for s in profile.skills}

    # 1. Direct 'related' relations in taxonomy
    # Check outgoing relations from candidate skills to gap
    for c_slug, c_sk in cand_slugs.items():
        relations = repo.get_relations(c_slug, kind="related")
        for rel in relations:
            if rel.related_slug == gap_slug:
                hint = f"You know {c_sk.name}, which is closely related to {gap_name}."
                if hint not in hints:
                    hints.append(hint)

        # Check relations from gap to candidate skills
        gap_rels = repo.get_relations(gap_slug, kind="related")
        for rel in gap_rels:
            if rel.related_slug == c_slug:
                hint = f"You know {c_sk.name}, which directly links to {gap_name}."
                if hint not in hints:
                    hints.append(hint)

    # 2. Sibling edges (shared parent or same subcategory)
    for c_slug, c_sk in cand_slugs.items():
        if len(hints) >= max_hints:
            break
        tax_cand = repo.get_skill(c_slug)
        if tax_cand is not None:
            if tax_cand.parent_slug and tax_cand.parent_slug == gap_skill.parent_slug:
                hint = f"You know {c_sk.name}, so learn {gap_name} next (adjacent sibling)."
                if hint not in hints:
                    hints.append(hint)
            else:
                c_anc = [a.slug for a in repo.get_ancestors(c_slug) if a.level == 2]
                g_anc = [a.slug for a in repo.get_ancestors(gap_slug) if a.level == 2]
                if c_anc and g_anc and c_anc[0] == g_anc[0]:
                    hint = f"You know {c_sk.name}, so learn {gap_name} next (same domain)."
                    if hint not in hints:
                        hints.append(hint)

    return hints[:max_hints]


def analyze_gaps(
    requirements: list[JobRequirement],
    breakdown: list[RequirementCredit],
    profile: SkillProfile,
    repo: TaxonomyRepository | None = None,
    credit_threshold: float = 0.85,
) -> list[GapItem]:
    """Identify unmet requirements and generate upskilling guidance."""
    gaps: list[GapItem] = []

    req_map = {r.skill_slug: r for r in requirements}

    for credit in breakdown:
        req = req_map.get(credit.requirement_slug)
        if req is None:
            continue

        # If credit is below threshold or skill is missing
        if credit.credit < credit_threshold or credit.match_type == "missing":
            hints = generate_upskilling_hints(
                gap_slug=req.skill_slug,
                gap_name=req.name,
                profile=profile,
                repo=repo,
            )
            gaps.append(
                GapItem(
                    skill_slug=req.skill_slug,
                    skill_name=req.name,
                    required=req.required,
                    importance=req.importance,
                    required_proficiency=format_required_proficiency(req),
                    current_proficiency=format_current_proficiency(credit, profile),
                    upskilling_hints=hints,
                )
            )

    return gaps
