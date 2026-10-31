"""Step 6.2: SearchPlan schema and search planning logic (LLM + rule-based fallback)."""

from __future__ import annotations

import re
from pathlib import Path

import structlog
from pydantic import BaseModel, Field

from talentgraph.db.repositories.taxonomy import TaxonomyRepository, get_taxonomy_repository
from talentgraph.llm.client import LLMClient

log = structlog.get_logger(__name__)

ROOT = Path(__file__).resolve().parents[4]
PROMPT_PATH = ROOT / "src" / "talentgraph" / "llm" / "prompts" / "search_plan.md"

SENIORITY_KEYWORDS = ("junior", "mid", "senior", "lead", "staff", "principal")
DOMAINS = (
    "fintech",
    "healthcare",
    "ecommerce",
    "legal",
    "gaming",
    "biotech",
    "education",
    "cybersecurity",
    "defense",
    "aerospace",
)


class RawSearchPlan(BaseModel):
    must_skills: list[str] = Field(default_factory=list)
    should_skills: list[str] = Field(default_factory=list)
    min_years: float | None = None
    domain: str | None = None
    seniority: str | None = None


class SearchPlan(BaseModel):
    query: str
    must_skills: list[str] = Field(
        default_factory=list, description="Mandatory canonical skill slugs"
    )
    should_skills: list[str] = Field(
        default_factory=list, description="Desirable canonical skill slugs"
    )
    min_years: float | None = Field(default=None, description="Minimum years of experience")
    domain: str | None = Field(default=None, description="Target domain or industry")
    seniority: str | None = Field(default=None, description="Target seniority level")


def _normalize_skill_terms(terms: list[str], repo: TaxonomyRepository) -> list[str]:
    """Map raw skill terms from planner to canonical slugs."""
    canonical_slugs: list[str] = []
    for term in terms:
        t_clean = term.strip().lower()
        if not t_clean:
            continue
        # Direct slug match
        if t_clean in repo.slug_map:
            canonical_slugs.append(t_clean)
            continue
        # Alias lookup
        canon = repo.resolve_alias(t_clean)
        if canon:
            canonical_slugs.append(canon.slug)
            continue
        # Hyphenated lookup
        hyphen = t_clean.replace(" ", "-")
        if hyphen in repo.slug_map:
            canonical_slugs.append(hyphen)
            continue
        canon_h = repo.resolve_alias(hyphen)
        if canon_h:
            canonical_slugs.append(canon_h.slug)
            continue
        canonical_slugs.append(hyphen)
    return list(dict.fromkeys(canonical_slugs))


def keyword_plan(query: str, repo: TaxonomyRepository | None = None) -> SearchPlan:
    """Deterministic rule-based query parser (plan §6.4 Step 4: degradation without LLM)."""
    repo = repo or get_taxonomy_repository()
    q_lower = query.lower()

    # 1. Experience years
    min_years: float | None = None
    y_match = re.search(r"(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)", q_lower)
    if y_match:
        min_years = float(y_match.group(1))

    # 2. Seniority
    seniority: str | None = None
    for s in SENIORITY_KEYWORDS:
        if re.search(rf"\b{s}\b", q_lower):
            seniority = s
            break

    # 3. Domain
    domain: str | None = None
    for d in DOMAINS:
        if re.search(rf"\b{d}\b", q_lower):
            domain = d
            break

    # 4. Partition must vs should skills
    must_raw: list[str] = []
    should_raw: list[str] = []

    # Check for should clauses ("some ...", "ideally ...", "nice to have ...")
    should_part = ""
    must_part = q_lower
    for sep in ("ideally", "nice to have", "plus if", "prefer", "bonus", "some "):
        if sep in q_lower:
            parts = q_lower.split(sep, 1)
            must_part = parts[0]
            should_part = parts[1]
            break

    # Extract skill mentions from parts
    for alias_norm, alias_rec in repo.alias_map.items():
        if len(alias_norm) < 3 and alias_norm not in (
            "go",
            "c",
            "r",
            "ai",
            "ml",
            "ui",
            "ux",
            "qa",
            "ip",
        ):
            continue
        pattern = rf"\b{re.escape(alias_norm)}\b"
        if re.search(pattern, must_part):
            must_raw.append(alias_rec.slug)
        elif should_part and re.search(pattern, should_part):
            should_raw.append(alias_rec.slug)

    must_skills = list(dict.fromkeys(must_raw))
    should_skills = [s for s in dict.fromkeys(should_raw) if s not in must_skills]

    return SearchPlan(
        query=query,
        must_skills=must_skills,
        should_skills=should_skills,
        min_years=min_years,
        domain=domain,
        seniority=seniority,
    )


async def plan_search(
    query: str,
    llm: LLMClient | None = None,
    repo: TaxonomyRepository | None = None,
) -> tuple[SearchPlan, bool]:
    """Generate structured SearchPlan using LLM with deterministic fallback.

    Returns:
        (plan, used_llm)
    """
    repo = repo or get_taxonomy_repository()

    if llm is None:
        return keyword_plan(query, repo), False

    system_prompt = (
        PROMPT_PATH.read_text(encoding="utf-8")
        if PROMPT_PATH.exists()
        else "Extract must_skills, should_skills, min_years, domain, seniority into JSON."
    )

    try:
        raw_plan = await llm.extract(
            RawSearchPlan,
            system=system_prompt,
            user=f"Search Query: {query}",
        )
        must_skills = _normalize_skill_terms(raw_plan.must_skills, repo)
        should_skills = _normalize_skill_terms(raw_plan.should_skills, repo)

        plan = SearchPlan(
            query=query,
            must_skills=must_skills,
            should_skills=should_skills,
            min_years=raw_plan.min_years,
            domain=raw_plan.domain,
            seniority=raw_plan.seniority,
        )
        return plan, True
    except Exception as exc:
        log.warning("plan_search.llm_failed", error=str(exc))
        # Graceful fallback to keyword parser
        return keyword_plan(query, repo), False
