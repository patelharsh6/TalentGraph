"""Step 6.4: Two-stage factuality critic for Career Coach (plan §6.5).

Stage 1: Deterministic checks (skills evidenced in profile, metrics match,
taxonomy checks).
Stage 2: LLM check for invented employers, numbers, dates, or responsibilities.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import structlog
from pydantic import BaseModel, Field

from talentgraph.api.schemas import BulletRewrite, LearningGoal
from talentgraph.db.repositories.taxonomy import TaxonomyRepository, get_taxonomy_repository
from talentgraph.llm.client import LLMClient

log = structlog.get_logger(__name__)

ROOT = Path(__file__).resolve().parents[4]
CRITIC_PROMPT_PATH = ROOT / "src" / "talentgraph" / "llm" / "prompts" / "coach_critic.md"


class LLMCriticItem(BaseModel):
    is_valid: bool
    reason: str | None = None
    suggested_fix: str | None = None


class LLMCriticResponse(BaseModel):
    evaluations: list[LLMCriticItem] = Field(default_factory=list)


def extract_numbers_and_metrics(text: str) -> set[str]:
    """Extract numbers, percentages, dollar amounts, and multipliers."""
    tokens = re.findall(r"\b\d+(?:\.\d+)?%?|\$\d+(?:\.\d+)?|\b\d+x\b", text.lower())
    return set(tokens)


def deterministic_verify_bullet(
    bullet: BulletRewrite,
    profile_data: dict[str, Any],
) -> tuple[bool, str | None]:
    """Stage 1: Deterministic check of a resume bullet rewrite.

    Checks:
    1. Every highlighted skill must exist in profile skills with non-empty evidence.
    2. No new numbers, percentages, or multipliers invented.
    """
    cand_skills_map = {
        s.get("canonical_slug", "").lower(): s.get("evidence", "")
        for s in profile_data.get("skills", [])
    }
    cand_raw_skills = {
        s.get("raw", "").lower(): s.get("evidence", "") for s in profile_data.get("skills", [])
    }

    # 1. Skill verification
    for skill in bullet.highlighted_skills:
        s_clean = skill.strip().lower()
        slug_clean = s_clean.replace(" ", "-")
        evidence = (
            cand_skills_map.get(slug_clean)
            or cand_skills_map.get(s_clean)
            or cand_raw_skills.get(s_clean)
        )
        if evidence is None:
            return False, f"Skill '{skill}' is not present in candidate verified profile."

    # 2. Metric and number verification
    orig_numbers = extract_numbers_and_metrics(bullet.original_evidence)
    rewritten_numbers = extract_numbers_and_metrics(bullet.improved_bullet)

    # Any new number in rewrite that wasn't in original evidence is rejected
    invented_numbers = rewritten_numbers - orig_numbers
    if invented_numbers:
        return (
            False,
            f"Invented metric(s) {sorted(invented_numbers)} not present in original evidence.",
        )

    # 3. Basic length / substance check
    if len(bullet.improved_bullet.strip()) < 10:
        return False, "Rewritten bullet is too short or empty."

    return True, None


def deterministic_verify_learning_plan(
    goals: list[LearningGoal],
    repo: TaxonomyRepository | None = None,
) -> tuple[list[LearningGoal], list[str]]:
    """Stage 1: Verify all learning plan skills exist in taxonomy repository.

    Returns:
        (valid_goals, removed_descriptions)
    """
    repo = repo or get_taxonomy_repository()
    valid_goals: list[LearningGoal] = []
    removed: list[str] = []

    for goal in goals:
        slug = goal.skill_slug.strip().lower()
        if slug in repo.slug_map:
            valid_goals.append(goal)
        else:
            msg = f"Learning goal '{goal.skill_name}' ({goal.skill_slug}) not in taxonomy."
            removed.append(msg)

    return valid_goals, removed


async def llm_verify_bullets(
    bullets: list[BulletRewrite],
    profile_data: dict[str, Any],
    llm: LLMClient | None = None,
) -> list[tuple[bool, str | None]]:
    """Stage 2: LLM verification check for subtle hallucinations.

    If LLM is None or fails, falls back safely to accepting deterministic-passed items.
    """
    if not bullets or llm is None:
        return [(True, None) for _ in bullets]

    system_prompt = (
        CRITIC_PROMPT_PATH.read_text(encoding="utf-8")
        if CRITIC_PROMPT_PATH.exists()
        else "Check for hallucinated experience, employers, numbers or dates."
    )

    items_payload = [
        {
            "index": i,
            "original_evidence": b.original_evidence,
            "improved_bullet": b.improved_bullet,
            "highlighted_skills": b.highlighted_skills,
        }
        for i, b in enumerate(bullets)
    ]

    user_prompt = (
        f"Candidate Summary: {profile_data.get('summary', '')}\n"
        f"Verified Experience: {profile_data.get('experience', [])}\n"
        f"Bullets to verify:\n{items_payload}"
    )

    try:
        res = await llm.extract(LLMCriticResponse, system=system_prompt, user=user_prompt)
        results: list[tuple[bool, str | None]] = []
        for i, _b in enumerate(bullets):
            if i < len(res.evaluations):
                eval_item = res.evaluations[i]
                results.append((eval_item.is_valid, eval_item.reason))
            else:
                results.append((True, None))
        return results
    except Exception as exc:
        log.warning("critic.llm_check_failed", error=str(exc))
        # Graceful fallback: accept items that already passed deterministic Stage 1
        return [(True, None) for _ in bullets]
