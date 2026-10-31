"""Step 4.2: pure scoring functions (plan §6.3).

Per-requirement credit, weighted skill score, years factor, missing-skill penalty.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from talentgraph.core.schemas.matching import (
    JobRequirement,
    JobRequirements,
    MatchResult,
    RequirementCredit,
)
from talentgraph.core.schemas.skills import NormalizedSkill, SkillProfile
from talentgraph.db.repositories.taxonomy import TaxonomyRepository

if TYPE_CHECKING:
    from talentgraph.embeddings.skill_index import SkillIndex

SENIORITY_YEARS: dict[str, float] = {
    "entry": 1.0,
    "junior": 2.0,
    "associate": 2.0,
    "mid": 3.0,
    "intermediate": 3.0,
    "senior": 5.0,
    "lead": 7.0,
    "staff": 8.0,
    "principal": 10.0,
    "director": 12.0,
    "executive": 15.0,
}


@dataclass(frozen=True)
class ScoringConfig:
    alpha_skill: float = 0.70
    beta_experience: float = 0.30
    lambda_nice: float = 0.35
    sim_exact: float = 1.0
    sim_descendant: float = 0.9
    sim_ancestor_or_sibling: float = 0.6
    sim_embedding_floor: float = 0.55
    depth_base: float = 0.6
    depth_weight: float = 0.4
    penalty_per_missing: float = 0.10
    penalty_min_importance: int = 4


DEFAULT_SCORING_CONFIG = ScoringConfig()


def get_required_years(job: JobRequirements) -> float:
    """Determine minimum experience years required for seniority level."""
    if job.min_total_experience_years is not None and job.min_total_experience_years > 0:
        return float(job.min_total_experience_years)
    if job.seniority and job.seniority.lower() in SENIORITY_YEARS:
        return SENIORITY_YEARS[job.seniority.lower()]
    return 3.0


def get_candidate_experience_years(profile: SkillProfile) -> float:
    """Extract candidate total relevant experience years."""
    if "total_experience_years" in profile.meta:
        try:
            return float(profile.meta["total_experience_years"])
        except (ValueError, TypeError):
            pass
    if profile.skills:
        return max((s.years for s in profile.skills), default=0.0)
    return 0.0


def calculate_depth(
    skill: NormalizedSkill,
    min_years: float | None,
    config: ScoringConfig = DEFAULT_SCORING_CONFIG,
) -> float:
    """Calculate depth factor in [0, 1] based on years or proficiency level."""
    if min_years is not None and min_years > 0:
        return min(1.0, max(0.0, skill.years / min_years))
    # Proficiency-based depth if min_years is unset
    if skill.years > 0:
        return min(1.0, max(0.0, skill.years / 3.0))
    return min(1.0, max(0.0, skill.proficiency / 3.0))


def get_subcategory_slug(slug: str, repo: TaxonomyRepository) -> str | None:
    """Find the subcategory level (level 2) slug for a skill."""
    sk = repo.get_skill(slug)
    if sk is None:
        return None
    if sk.level == 2:
        return sk.slug
    for anc in repo.get_ancestors(slug):
        if anc.level == 2:
            return anc.slug
    return None


def compute_skill_similarity(
    cand_slug: str,
    req_slug: str,
    repo: TaxonomyRepository | None = None,
    skill_index: SkillIndex | None = None,
    config: ScoringConfig = DEFAULT_SCORING_CONFIG,
) -> tuple[float, str]:
    """Compute taxonomy/embedding similarity between candidate skill and requirement."""
    if cand_slug == req_slug:
        return config.sim_exact, "exact"

    if repo is not None:
        # Check if candidate is descendant of requirement
        cand_ancestors = {a.slug for a in repo.get_ancestors(cand_slug)}
        if req_slug in cand_ancestors:
            return config.sim_descendant, "descendant"

        # Check if candidate is ancestor of requirement
        req_ancestors = {a.slug for a in repo.get_ancestors(req_slug)}
        if cand_slug in req_ancestors:
            return config.sim_ancestor_or_sibling, "ancestor_or_sibling"

        # Check if siblings (same parent or same subcategory)
        c_sk = repo.get_skill(cand_slug)
        r_sk = repo.get_skill(req_slug)
        if c_sk is not None and r_sk is not None:
            if c_sk.parent_slug and c_sk.parent_slug == r_sk.parent_slug:
                return config.sim_ancestor_or_sibling, "ancestor_or_sibling"
            c_sub = get_subcategory_slug(cand_slug, repo)
            r_sub = get_subcategory_slug(req_slug, repo)
            if c_sub is not None and c_sub == r_sub:
                return config.sim_ancestor_or_sibling, "ancestor_or_sibling"

    # Embedding fallback
    if skill_index is not None:
        try:
            store = skill_index.store
            # Check if store has vectors
            if (
                hasattr(store, "_ids")
                and hasattr(store, "_vectors")
                and cand_slug in store._ids
                and req_slug in store._ids
            ):
                idx_c = store._ids.index(cand_slug)
                idx_r = store._ids.index(req_slug)
                vec_c = store._vectors[idx_c]
                vec_r = store._vectors[idx_r]
                cos_sim = float(np.dot(vec_c, vec_r))
                if cos_sim >= config.sim_embedding_floor:
                    return cos_sim, "embedding"
        except Exception:
            pass

    return 0.0, "missing"


def calculate_requirement_credit(
    req: JobRequirement,
    profile: SkillProfile,
    repo: TaxonomyRepository | None = None,
    skill_index: SkillIndex | None = None,
    config: ScoringConfig = DEFAULT_SCORING_CONFIG,
) -> RequirementCredit:
    """Calculate the best match and credit for a single job requirement against a profile."""
    weight = req.importance * (1.0 if req.required else config.lambda_nice)

    best_credit = 0.0
    best_cand: NormalizedSkill | None = None
    best_sim = 0.0
    best_match_type = "missing"
    best_depth = 0.0

    for cand_skill in profile.skills:
        sim, match_type = compute_skill_similarity(
            cand_skill.slug, req.skill_slug, repo=repo, skill_index=skill_index, config=config
        )
        if sim > 0.0:
            depth = calculate_depth(cand_skill, req.min_years, config=config)
            credit = sim * (config.depth_base + config.depth_weight * depth)
            if credit > best_credit:
                best_credit = credit
                best_cand = cand_skill
                best_sim = sim
                best_match_type = match_type
                best_depth = depth

    return RequirementCredit(
        requirement_slug=req.skill_slug,
        requirement_name=req.name,
        required=req.required,
        importance=req.importance,
        weight=weight,
        matched_slug=best_cand.slug if best_cand else None,
        matched_name=best_cand.name if best_cand else None,
        match_type=best_match_type,
        similarity=best_sim,
        depth=best_depth,
        credit=best_credit,
        contribution=0.0,  # Will be assigned during calculate_skill_score
    )


def calculate_skill_score(
    credits: list[RequirementCredit],
) -> tuple[float, list[RequirementCredit]]:
    """Calculate S_skill = sum(w_r * credit_r) / sum(w_r) and assign per-item contributions.

    This ensures sum(item.contribution for item in credits) == S_skill exactly (Exit Criterion 4-B).
    """
    total_weight = sum(c.weight for c in credits)
    if total_weight <= 0.0:
        return 0.0, credits

    updated_credits: list[RequirementCredit] = []
    total_skill_score = 0.0

    for c in credits:
        contrib = (c.weight * c.credit) / total_weight
        total_skill_score += contrib
        updated_credits.append(
            RequirementCredit(
                requirement_slug=c.requirement_slug,
                requirement_name=c.requirement_name,
                required=c.required,
                importance=c.importance,
                weight=c.weight,
                matched_slug=c.matched_slug,
                matched_name=c.matched_name,
                match_type=c.match_type,
                similarity=c.similarity,
                depth=c.depth,
                credit=c.credit,
                contribution=contrib,
            )
        )

    return total_skill_score, updated_credits


def calculate_experience_score(
    profile: SkillProfile,
    job: JobRequirements,
) -> float:
    """Calculate S_exp = min(1, relevant_years / years_for_seniority)."""
    req_years = get_required_years(job)
    cand_years = get_candidate_experience_years(profile)
    return min(1.0, max(0.0, cand_years / max(1.0, req_years)))


def calculate_penalty(
    credits: list[RequirementCredit],
    config: ScoringConfig = DEFAULT_SCORING_CONFIG,
) -> float:
    """Penalty of 0.1 per missing required skill with importance >= 4."""
    penalty = 0.0
    for c in credits:
        if c.required and c.importance >= config.penalty_min_importance and c.credit == 0.0:
            penalty += config.penalty_per_missing
    return penalty


def calculate_match_score(
    profile: SkillProfile,
    job: JobRequirements,
    *,
    repo: TaxonomyRepository | None = None,
    skill_index: SkillIndex | None = None,
    config: ScoringConfig = DEFAULT_SCORING_CONFIG,
    threshold: float = 0.60,
    preset: str | None = None,
) -> MatchResult:
    """Compute complete match score, breakdown, and components."""
    # 1. Per-requirement credits
    raw_credits = [
        calculate_requirement_credit(
            req, profile, repo=repo, skill_index=skill_index, config=config
        )
        for req in job.requirements
    ]

    # 2. Skill score and per-item contributions
    s_skill, breakdown = calculate_skill_score(raw_credits)

    # 3. Experience score
    s_exp = calculate_experience_score(profile, job)

    # 4. Penalty
    penalty = calculate_penalty(breakdown, config=config)

    # 5. Final score
    raw_score = config.alpha_skill * s_skill + config.beta_experience * s_exp - penalty
    final_score = max(0.0, min(1.0, raw_score))

    is_match = final_score >= threshold

    return MatchResult(
        schema_version="1.0",
        job_id=job.job_id,
        candidate_id=str(profile.candidate_id) if profile.candidate_id else None,
        score=round(final_score, 4),
        is_match=is_match,
        threshold=threshold,
        preset=preset,
        components={
            "skill_score": round(s_skill, 4),
            "experience_score": round(s_exp, 4),
            "penalty": round(penalty, 4),
            "raw_score": round(raw_score, 4),
        },
        breakdown=breakdown,
        gaps=[],  # Populated by gap analysis in Step 4.4 / MatchingAgent
    )
