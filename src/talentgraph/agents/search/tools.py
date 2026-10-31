"""Step 6.2: The four tools for the Talent Search agent (plan §6.4).

1. search_skills: resolves query terms to canonical taxonomy skill slugs.
2. filter_candidates: hard filtering over skills, experience years, and domain.
3. semantic_candidates: nearest-neighbor candidate retrieval from CandidateIndex.
4. match_candidate: scores candidate against search plan using MatchingAgent scorer.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import UUID

from talentgraph.agents.matching.scoring import calculate_match_score
from talentgraph.agents.search.plan import SearchPlan
from talentgraph.core.schemas.matching import JobRequirement, JobRequirements
from talentgraph.core.schemas.skills import NormalizedSkill, SkillProfile
from talentgraph.db.in_memory import get_all_candidates_in_memory, get_candidate_in_memory
from talentgraph.db.repositories.taxonomy import TaxonomyRepository, get_taxonomy_repository
from talentgraph.embeddings.candidate_index import CandidateIndex, get_candidate_index
from talentgraph.embeddings.skill_index import SkillIndex, get_skill_index

ROOT = Path(__file__).resolve().parents[4]
PROFILES_DIR = ROOT / "data" / "profiles"


def search_skills(
    text: str,
    repo: TaxonomyRepository | None = None,
    skill_index: SkillIndex | None = None,
    limit: int = 5,
) -> list[str]:
    """Tool 1: Resolve plain-English skill terms into canonical slugs (plan §6.4)."""
    repo = repo or get_taxonomy_repository()
    results: list[str] = []
    t_clean = text.strip().lower()

    # 1. Exact slug or name
    if t_clean in repo.slug_map:
        results.append(t_clean)
    for s in repo.skills:
        if s.name.lower() == t_clean and s.slug not in results:
            results.append(s.slug)

    # 2. Aliases
    canon = repo.resolve_alias(t_clean)
    if canon and canon.slug not in results:
        results.append(canon.slug)

    # 3. Vector search via skill_index
    try:
        idx = skill_index or get_skill_index()
        hits = idx.query(text, k=limit)
        for h in hits:
            if h.id not in results:
                results.append(h.id)
    except Exception:
        pass

    return results[:limit]


def _load_profile(candidate_id: str) -> tuple[SkillProfile, dict[str, Any]] | None:
    """Load profile from in-memory store or data/profiles."""
    # Check in-memory store by UUID
    try:
        u_id = UUID(candidate_id)
        mem = get_candidate_in_memory(u_id)
        if mem is not None:
            raw_meta = {
                "industry": "general",
                "total_experience_years": len(mem.parsed.experience) * 2.5,
            }
            return mem.profile, raw_meta
    except (ValueError, TypeError):
        pass

    # Check data/profiles JSON files
    p_path = PROFILES_DIR / f"{candidate_id}.gt.json"
    if p_path.exists():
        data = json.loads(p_path.read_text(encoding="utf-8"))
        tot_exp = float(data.get("meta", {}).get("total_experience_years", 3.0))

        skills = [
            NormalizedSkill(
                slug=s.get("canonical_slug") or s.get("raw", "").lower().replace(" ", "-"),
                name=s.get("raw", ""),
                years=min(tot_exp, 4.0),
                proficiency=3,
                evidence=[s.get("evidence", "")] if s.get("evidence") else [],
            )
            for s in data.get("skills", [])
        ]
        profile = SkillProfile(
            skills=skills,
            meta=data.get("meta", {}),
        )
        return profile, data

    return None


def filter_candidates(
    skill_ids: list[str],
    min_years: float | None = None,
    domain: str | None = None,
    limit: int = 50,
) -> list[str]:
    """Tool 2: Hard filter candidates matching skills, min_years, and domain (plan §6.4)."""
    matched_ids: list[str] = []
    norm_skills = [s.strip().lower() for s in skill_ids if s]

    # Iterate through ground truth profile files
    for p_path in sorted(PROFILES_DIR.glob("*.gt.json")):
        cid = p_path.name.replace(".gt.json", "")
        loaded = _load_profile(cid)
        if not loaded:
            continue
        profile, data = loaded
        meta = data.get("meta", {})

        # Domain filter
        if domain:
            cand_domain = str(meta.get("industry", "")).lower()
            if domain.lower() not in cand_domain and cand_domain not in domain.lower():
                continue

        # Experience years filter
        if min_years is not None:
            cand_years = float(meta.get("total_experience_years", 0.0))
            if cand_years < min_years:
                continue

        # Skills check
        if norm_skills:
            cand_slugs = {s.slug for s in profile.skills}
            # Matches if candidate has at least one of the target skills
            if any(req in cand_slugs for req in norm_skills):
                matched_ids.append(cid)
        else:
            matched_ids.append(cid)

        if len(matched_ids) >= limit:
            break

    # Also check in-memory store
    for mem in get_all_candidates_in_memory():
        cid_str = str(mem.id)
        if cid_str in matched_ids:
            continue
        if norm_skills:
            cand_slugs = {s.slug for s in mem.profile.skills}
            if any(req in cand_slugs for req in norm_skills):
                matched_ids.append(cid_str)
        else:
            matched_ids.append(cid_str)

    return matched_ids


def semantic_candidates(
    text: str,
    candidate_index: CandidateIndex | None = None,
    k: int = 20,
) -> list[dict[str, Any]]:
    """Tool 3: Vector retrieval from Chroma / NumPy CandidateIndex (plan §6.4)."""
    idx = candidate_index or get_candidate_index()
    hits = idx.query(text, k=k)
    return [
        {
            "candidate_id": h.id,
            "similarity": round(h.score, 4),
            "metadata": h.metadata,
        }
        for h in hits
    ]


def match_candidate(
    candidate_id: str,
    plan: SearchPlan,
    repo: TaxonomyRepository | None = None,
    skill_index: SkillIndex | None = None,
) -> dict[str, Any] | None:
    """Tool 4: Score candidate against search plan as a synthetic job (plan §6.4)."""
    loaded = _load_profile(candidate_id)
    if not loaded:
        return None
    profile, raw_data = loaded
    repo = repo or get_taxonomy_repository()

    # Build synthetic job requirements from SearchPlan
    reqs: list[JobRequirement] = []
    for s in plan.must_skills:
        s_obj = repo.slug_map.get(s)
        name = s_obj.name if s_obj else s.replace("-", " ").title()
        reqs.append(
            JobRequirement(
                skill_slug=s,
                name=name,
                required=True,
                importance=4,
                min_years=plan.min_years or 1.0,
            )
        )
    for s in plan.should_skills:
        s_obj = repo.slug_map.get(s)
        name = s_obj.name if s_obj else s.replace("-", " ").title()
        reqs.append(
            JobRequirement(
                skill_slug=s,
                name=name,
                required=False,
                importance=2,
                min_years=0.5,
            )
        )

    synthetic_job = JobRequirements(
        title=f"Search Query: {plan.query[:50]}",
        min_total_experience_years=plan.min_years,
        seniority=plan.seniority,
        requirements=reqs,
    )

    match_result = calculate_match_score(
        profile,
        synthetic_job,
        repo=repo,
        skill_index=skill_index,
        threshold=0.50,
    )

    # Extract citations for satisfied must-have and should-have skills
    citations: dict[str, list[str]] = {}
    matched_skills: list[str] = []
    missing_skills: list[str] = []

    for req_credit in match_result.breakdown:
        req_name = req_credit.requirement_name
        if req_credit.credit > 0.0:
            matched_skills.append(req_name)
            # Find evidence in profile skills
            matching_skill = next(
                (s for s in profile.skills if s.slug == req_credit.matched_slug),
                None,
            )
            if matching_skill and matching_skill.evidence:
                citations[req_name] = matching_skill.evidence
            else:
                citations[req_name] = [f"Demonstrated proficiency in {req_name}"]
        else:
            missing_skills.append(req_name)

    # Build explanation reasons
    reasons: list[str] = []
    cand_years = float(raw_data.get("meta", {}).get("total_experience_years", 3.0))
    cand_ind = raw_data.get("meta", {}).get("industry", "general")

    if matched_skills:
        reasons.append(f"Demonstrates key skills: {', '.join(matched_skills[:4])}")
    if plan.min_years and cand_years >= plan.min_years:
        reasons.append(f"Meets experience requirement with {cand_years:.0f} years")
    if plan.domain and plan.domain.lower() in cand_ind.lower():
        reasons.append(f"Strong industry match in {cand_ind}")

    return {
        "candidate_id": candidate_id,
        "score": match_result.score,
        "is_match": match_result.is_match,
        "reasons": reasons,
        "citations": citations,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
    }
