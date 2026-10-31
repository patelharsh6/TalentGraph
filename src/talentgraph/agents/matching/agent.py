"""Step 4.5: MatchingAgent (score, breakdown, gaps, rank helper)."""

from __future__ import annotations

import time

import structlog

from talentgraph.agents.matching.gaps import analyze_gaps
from talentgraph.agents.matching.job_parser import JobParser
from talentgraph.agents.matching.scoring import ScoringConfig, calculate_match_score
from talentgraph.agents.matching.thresholds import load_presets, resolve_threshold
from talentgraph.config import Settings, get_settings
from talentgraph.core.schemas.matching import JobRequirements, MatchResult
from talentgraph.core.schemas.messages import AgentMessage, AgentName, AgentResult, QualityScore
from talentgraph.core.schemas.skills import SkillProfile
from talentgraph.db.repositories.taxonomy import TaxonomyRepository, get_taxonomy_repository
from talentgraph.embeddings.skill_index import SkillIndex, get_skill_index

log = structlog.get_logger(__name__)


class MatchingAgent:
    """Evaluates candidate SkillProfile against JobRequirements with explainable scoring."""

    name: AgentName = "matcher"

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        repo: TaxonomyRepository | None = None,
        skill_index: SkillIndex | None = None,
        job_parser: JobParser | None = None,
        config: ScoringConfig | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._repo = repo
        self._skill_index = skill_index
        self._job_parser = job_parser
        self._config = config or ScoringConfig()
        self._presets = load_presets()

    def _get_repo(self) -> TaxonomyRepository:
        if self._repo is None:
            self._repo = get_taxonomy_repository(self._settings.taxonomy_dir)
        return self._repo

    def _get_skill_index(self) -> SkillIndex:
        if self._skill_index is None:
            self._skill_index = get_skill_index()
        return self._skill_index

    def _get_job_parser(self) -> JobParser:
        if self._job_parser is None:
            self._job_parser = JobParser(settings=self._settings)
        return self._job_parser

    async def startup(self) -> None:
        """Warm up taxonomy and embeddings."""
        _ = self._get_repo()
        _ = self._get_skill_index()

    async def shutdown(self) -> None:
        """Clean up resources."""
        pass

    def compute_quality(self, result: MatchResult) -> QualityScore:
        """Matcher quality score: share of requirements evaluated and distance from threshold."""
        total_reqs = len(result.breakdown)
        if total_reqs == 0:
            return QualityScore(score=1.0, breakdown={"eval_share": 1.0, "margin": 0.0})

        evaluated = sum(1 for b in result.breakdown if b.match_type != "missing")
        eval_share = evaluated / total_reqs
        margin = min(1.0, abs(result.score - result.threshold) * 2.0)

        # Weighted combination: 70% evaluation coverage, 30% margin confidence
        quality_val = round(0.70 * eval_share + 0.30 * margin, 4)
        return QualityScore(
            score=quality_val,
            breakdown={"eval_share": round(eval_share, 4), "margin": round(margin, 4)},
        )

    async def match(
        self,
        profile: SkillProfile,
        job: JobRequirements | str,
        *,
        threshold: float | str | None = None,
    ) -> MatchResult:
        """Match a candidate profile against job requirements or text."""
        # 1. Resolve JobRequirements
        job_reqs: JobRequirements
        if isinstance(job, str):
            parser = self._get_job_parser()
            # If string is job_000 format, try loading from ground truth
            if job.startswith("job_") and len(job) <= 10:
                try:
                    job_reqs = JobParser.load_from_ground_truth(job)
                except Exception:
                    job_reqs = await parser.parse(job)
            else:
                job_reqs = await parser.parse(job)
        else:
            job_reqs = job

        # 2. Resolve threshold preset or numeric value
        thresh_val, preset_name = resolve_threshold(threshold, presets=self._presets)

        # 3. Calculate match score, credits, and breakdown
        repo = self._get_repo()
        skill_index = self._get_skill_index()
        result = calculate_match_score(
            profile=profile,
            job=job_reqs,
            repo=repo,
            skill_index=skill_index,
            config=self._config,
            threshold=thresh_val,
            preset=preset_name,
        )

        # 4. Analyze gaps and upskilling hints
        result.gaps = analyze_gaps(
            requirements=job_reqs.requirements,
            breakdown=result.breakdown,
            profile=profile,
            repo=repo,
        )

        return result

    async def rank(
        self,
        candidates: list[SkillProfile],
        job: JobRequirements | str,
        *,
        threshold: float | str | None = None,
    ) -> list[MatchResult]:
        """Rank multiple candidates against a job description in descending score order."""
        results: list[MatchResult] = []
        for cand in candidates:
            res = await self.match(cand, job, threshold=threshold)
            results.append(res)

        # Sort descending by score, tie-breaking by skill_score
        results.sort(
            key=lambda r: (r.score, r.components.get("skill_score", 0.0)),
            reverse=True,
        )
        return results

    async def handle(self, msg: AgentMessage) -> AgentResult:
        """Handle incoming AgentMessage protocol task."""
        t0 = time.perf_counter()
        payload = msg.payload
        try:
            profile_data = payload.get("profile")
            if isinstance(profile_data, dict):
                profile = SkillProfile.model_validate(profile_data)
            elif isinstance(profile_data, SkillProfile):
                profile = profile_data
            else:
                raise ValueError("Missing or invalid 'profile' in payload")

            job_data = payload.get("job")
            job: JobRequirements | str
            if isinstance(job_data, dict):
                job = JobRequirements.model_validate(job_data)
            elif isinstance(job_data, (str, JobRequirements)):
                job = job_data
            else:
                raise ValueError("Missing or invalid 'job' in payload")

            threshold = payload.get("threshold")
            result = await self.match(profile, job, threshold=threshold)

            quality = self.compute_quality(result)
            latency_ms = int((time.perf_counter() - t0) * 1000)

            return AgentResult(
                status="ok",
                data=result.model_dump(),
                quality=quality,
                latency_ms=latency_ms,
            )
        except Exception as exc:
            latency_ms = int((time.perf_counter() - t0) * 1000)
            log.warning("matching_agent.handle_failed", error=str(exc))
            return AgentResult(
                status="failed",
                data=None,
                quality=QualityScore(score=0.0),
                latency_ms=latency_ms,
                warnings=[str(exc)],
            )
