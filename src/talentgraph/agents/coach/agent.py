"""Step 6.4: Career Coach agent with factuality critic and feedback loop (feature F3)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import structlog
from pydantic import BaseModel, Field

from talentgraph.agents.coach.critic import (
    deterministic_verify_bullet,
    deterministic_verify_learning_plan,
    llm_verify_bullets,
)
from talentgraph.agents.matching.job_parser import JobParser
from talentgraph.agents.matching.scoring import calculate_match_score
from talentgraph.api.schemas import (
    BulletRewrite,
    CoachReport,
    InterviewQuestion,
    LearningGoal,
)
from talentgraph.config import Settings, get_settings
from talentgraph.core.errors import NotFound, ServiceUnavailable
from talentgraph.core.schemas.matching import JobRequirements
from talentgraph.core.schemas.skills import SkillProfile
from talentgraph.db.repositories.taxonomy import TaxonomyRepository, get_taxonomy_repository
from talentgraph.embeddings.skill_index import SkillIndex, get_skill_index
from talentgraph.llm.client import LLMClient, get_llm

log = structlog.get_logger(__name__)

ROOT = Path(__file__).resolve().parents[4]
GENERATE_PROMPT_PATH = ROOT / "src" / "talentgraph" / "llm" / "prompts" / "coach_generate.md"
PROFILES_DIR = ROOT / "data" / "profiles"


class RawCoachDraft(BaseModel):
    learning_rationales: dict[str, str] = Field(default_factory=dict)
    interview_questions: list[InterviewQuestion] = Field(default_factory=list)
    bullet_rewrites: list[BulletRewrite] = Field(default_factory=list)


class RevisedBulletsResponse(BaseModel):
    revised_bullets: list[BulletRewrite] = Field(default_factory=list)


class CoachAgent:
    """Career coach agent implementing generate -> critic -> revise loop (plan §6.5)."""

    def __init__(
        self,
        settings: Settings | None = None,
        llm: LLMClient | None = None,
        repo: TaxonomyRepository | None = None,
        skill_index: SkillIndex | None = None,
        enable_llm: bool = True,
    ) -> None:
        self.settings = settings or get_settings()
        self.enable_llm = enable_llm
        self.llm = (llm if llm is not None else get_llm(self.settings)) if enable_llm else None
        self.repo = repo or get_taxonomy_repository(self.settings.taxonomy_dir)
        self.skill_index = skill_index or get_skill_index()

        # Cache keyed by (candidate_id, job_id) for Exit Criterion 6-D (0 LLM calls on repeat)
        self._cache: dict[str, CoachReport] = {}

    def clear_cache(self) -> None:
        self._cache.clear()

    async def coach(
        self,
        candidate_id: str,
        job_id: str | None = None,
        job_reqs: JobRequirements | None = None,
        profile_data: dict[str, Any] | None = None,
    ) -> CoachReport:
        """Generate Career Coach report with strict verification and zero hallucinations."""
        cache_key = f"{candidate_id}::{job_id or 'synthetic'}"
        if cache_key in self._cache:
            log.debug("coach.cache_hit", key=cache_key)
            return self._cache[cache_key]

        # Exit Criterion 6-C degradation check:
        if not self.enable_llm or self.llm is None:
            log.warning("coach.llm_unavailable", candidate_id=candidate_id)
            raise ServiceUnavailable("Career Coach service requires LLM capabilities.")

        # 1. Load candidate profile if needed
        if profile_data is None:
            p_file = PROFILES_DIR / f"{candidate_id}.gt.json"
            if not p_file.exists():
                raise NotFound(f"Candidate profile {candidate_id} not found.")
            profile_data = json.loads(p_file.read_text(encoding="utf-8"))

        # Convert to SkillProfile for scoring
        skill_profile = SkillProfile.model_validate(profile_data)

        # 2. Load job requirements if needed
        if job_reqs is None:
            if job_id:
                job_reqs = JobParser.load_from_ground_truth(job_id)
            else:
                raise NotFound("Either job_id or job_reqs must be provided.")

        # 3. Calculate match score and gap analysis
        match_result = calculate_match_score(
            skill_profile,
            job_reqs,
            repo=self.repo,
            skill_index=self.skill_index,
        )

        # 4. Build Learning Plan ordered by taxonomy prerequisite edges
        raw_learning_goals = self._build_ordered_learning_plan(match_result.gaps)
        learning_plan, removed_lp = deterministic_verify_learning_plan(
            raw_learning_goals, self.repo
        )
        removed_claims: list[str] = list(removed_lp)

        # 5. Extract candidates for resume bullet rewrites
        existing_bullets: list[str] = []
        for exp in profile_data.get("experience", []):
            for resp in exp.get("responsibilities", []):
                if len(resp.strip()) > 15:
                    existing_bullets.append(resp.strip())
        existing_bullets = existing_bullets[:5]

        # Weakest requirements for interview prep
        weak_reqs = sorted(
            match_result.breakdown,
            key=lambda c: (1 if c.required else 0, -c.importance, c.credit),
            reverse=True,
        )
        weakest_names = [c.requirement_name for c in weak_reqs[:5]]

        # 6. LLM Generation
        draft = await self._generate_draft(
            profile_data=profile_data,
            weakest_reqs=weakest_names,
            existing_bullets=existing_bullets,
            learning_goals=learning_plan,
        )

        interview_questions = draft.interview_questions
        candidate_bullets = draft.bullet_rewrites

        # 7. Subgraph feedback loop: generate -> critic -> (revise -> critic) (max 2 revisions)
        verified_bullets: list[BulletRewrite] = []
        revisions_count = 0

        pending_bullets = candidate_bullets[:5]

        while pending_bullets and revisions_count <= 2:
            passed_stage1: list[BulletRewrite] = []
            failed_stage1: list[tuple[BulletRewrite, str]] = []

            # Stage 1: Deterministic check
            for b in pending_bullets:
                ok, reason = deterministic_verify_bullet(b, profile_data)
                if ok:
                    passed_stage1.append(b)
                else:
                    failed_stage1.append((b, reason or "Unsupported claims in rewrite"))

            # Stage 2: LLM check on passed items
            passed_stage2: list[BulletRewrite] = []
            failed_stage2: list[tuple[BulletRewrite, str]] = []

            if passed_stage1:
                llm_evals = await llm_verify_bullets(passed_stage1, profile_data, self.llm)
                for b, (ok, reason) in zip(passed_stage1, llm_evals, strict=False):
                    if ok:
                        passed_stage2.append(b)
                    else:
                        failed_stage2.append((b, reason or "LLM critic flagged unsupported claim"))

            # Accumulate newly verified bullets
            verified_bullets.extend(passed_stage2)

            all_failed = failed_stage1 + failed_stage2
            if not all_failed or revisions_count >= 2:
                # No more revisions or reached cap: drop remaining failed and record
                for b, r in all_failed:
                    removed_claims.append(f"Removed rewrite '{b.improved_bullet}': {r}")
                break

            # Attempt revision with feedback
            revisions_count += 1
            log.info("coach.revise_attempt", revision=revisions_count, num_failed=len(all_failed))
            revised = await self._revise_bullets(all_failed, profile_data)
            pending_bullets = revised

        report = CoachReport(
            candidate_id=candidate_id,
            job_id=job_id,
            learning_plan=learning_plan,
            interview_questions=interview_questions[:5],
            bullet_rewrites=verified_bullets[:5],
            removed_claims=removed_claims,
            revisions_count=revisions_count,
        )

        self._cache[cache_key] = report
        return report

    def _build_ordered_learning_plan(self, gaps: list[Any]) -> list[LearningGoal]:
        """Order learning goals based on prerequisite/related edges in taxonomy."""
        goals: list[LearningGoal] = []
        if not gaps:
            return goals

        gap_slugs = [g.skill_slug for g in gaps]
        slug_to_gap = {g.skill_slug: g for g in gaps}

        # Check prerequisite edges
        prereq_graph: dict[str, list[str]] = {}
        for s in gap_slugs:
            rels = self.repo.get_relations(s, kind="prerequisite")
            prereqs = [r.related_slug for r in rels if r.related_slug in slug_to_gap]
            prereq_graph[s] = prereqs

        # Topological sort order
        ordered_slugs: list[str] = []
        visited: set[str] = set()

        def visit(node: str) -> None:
            if node in visited:
                return
            for prereq in prereq_graph.get(node, []):
                visit(prereq)
            visited.add(node)
            ordered_slugs.append(node)

        for s in gap_slugs:
            visit(s)

        for rank, s in enumerate(ordered_slugs, 1):
            gap_item = slug_to_gap[s]
            s_obj = self.repo.slug_map.get(s)
            name = s_obj.name if s_obj else gap_item.skill_name
            prereqs = [
                self.repo.slug_map[p].name
                for p in prereq_graph.get(s, [])
                if p in self.repo.slug_map
            ]

            goals.append(
                LearningGoal(
                    skill_slug=s,
                    skill_name=name,
                    rationale=f"Addresses key gap (importance {gap_item.importance}).",
                    prerequisites=prereqs,
                    recommended_order=rank,
                )
            )

        return goals

    async def _generate_draft(
        self,
        profile_data: dict[str, Any],
        weakest_reqs: list[str],
        existing_bullets: list[str],
        learning_goals: list[LearningGoal],
    ) -> RawCoachDraft:
        """Call LLM to generate initial coach content draft."""
        assert self.llm is not None
        system_prompt = (
            GENERATE_PROMPT_PATH.read_text(encoding="utf-8")
            if GENERATE_PROMPT_PATH.exists()
            else "You are a career coach. Generate goals, 5 interview questions, and rewrites."
        )

        verified_skills = [s.get("canonical_slug") for s in profile_data.get("skills", [])]
        user_content = (
            f"Candidate Summary: {profile_data.get('summary', '')}\n"
            f"Candidate Experience Bullets:\n{json.dumps(existing_bullets, indent=2)}\n"
            f"Verified Candidate Skills: {verified_skills}\n"
            f"Weakest Job Requirements: {weakest_reqs}\n"
            f"Target Learning Goals: {[g.skill_name for g in learning_goals]}\n\n"
            f"Generate 5 interview questions and improve bullets without inventing facts."
        )

        try:
            return await self.llm.extract(RawCoachDraft, system=system_prompt, user=user_content)
        except Exception as exc:
            log.warning("coach.generation_llm_failed", error=str(exc))
            # Fallback draft
            fallback_questions = [
                InterviewQuestion(
                    requirement_name=r,
                    question=f"Can you describe your experience and proficiency with {r}?",
                    target_competency=r,
                    preparation_tip=f"Highlight concrete projects where you applied {r}.",
                )
                for r in weakest_reqs[:5]
            ]
            fallback_rewrites = [
                BulletRewrite(
                    original_evidence=b,
                    improved_bullet=b,
                    highlighted_skills=[],
                    rationale="Preserved original bullet.",
                )
                for b in existing_bullets[:5]
            ]
            return RawCoachDraft(
                interview_questions=fallback_questions,
                bullet_rewrites=fallback_rewrites,
            )

    async def _revise_bullets(
        self,
        failed_items: list[tuple[BulletRewrite, str]],
        profile_data: dict[str, Any],
    ) -> list[BulletRewrite]:
        """Ask LLM to revise rejected bullets to fix critic objections."""
        assert self.llm is not None
        system_prompt = (
            "You are a strict career coach revising rejected resume bullet rewrites. "
            "Remove all invented numbers, companies, or tools. Ground every word in evidence."
        )

        objections = [
            {
                "original_evidence": b.original_evidence,
                "rejected_rewrite": b.improved_bullet,
                "rejection_reason": reason,
            }
            for b, reason in failed_items
        ]

        verified_skills = [s.get("canonical_slug") for s in profile_data.get("skills", [])]
        user_content = (
            f"Verified Candidate Skills: {verified_skills}\n"
            f"Rejected items:\n{json.dumps(objections, indent=2)}\n\n"
            f"Revise each rejected rewrite so that it strictly adheres to the original evidence."
        )

        try:
            res = await self.llm.extract(
                RevisedBulletsResponse, system=system_prompt, user=user_content
            )
            return res.revised_bullets
        except Exception as exc:
            log.warning("coach.revision_llm_failed", error=str(exc))
            return []
