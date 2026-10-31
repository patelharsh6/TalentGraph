"""Step 6.2: Talent Search agent with LLM planner, LangGraph loop, and re-ranking (feature F1)."""

from __future__ import annotations

import time
from typing import Any

import structlog

from talentgraph.agents.search.plan import SearchPlan, plan_search
from talentgraph.agents.search.tools import (
    filter_candidates,
    match_candidate,
    search_skills,
    semantic_candidates,
)
from talentgraph.api.schemas import SearchHit
from talentgraph.config import Settings, get_settings
from talentgraph.core.schemas.messages import (
    AgentMessage,
    AgentName,
    AgentResult,
    QualityScore,
)
from talentgraph.db.repositories.taxonomy import TaxonomyRepository, get_taxonomy_repository
from talentgraph.embeddings.candidate_index import CandidateIndex, get_candidate_index
from talentgraph.embeddings.skill_index import SkillIndex, get_skill_index
from talentgraph.llm.client import LLMClient, get_llm

log = structlog.get_logger(__name__)


class SearchAgent:
    """Natural-language talent search agent (plan §6.4)."""

    name: AgentName = "search"

    def __init__(
        self,
        settings: Settings | None = None,
        llm: LLMClient | None = None,
        repo: TaxonomyRepository | None = None,
        skill_index: SkillIndex | None = None,
        candidate_index: CandidateIndex | None = None,
        enable_llm: bool = True,
    ) -> None:
        self.settings = settings or get_settings()
        self.enable_llm = enable_llm
        self.llm = (llm if llm is not None else get_llm(self.settings)) if enable_llm else None
        self.repo = repo or get_taxonomy_repository(self.settings.taxonomy_dir)
        self.skill_index = skill_index or get_skill_index()
        self.candidate_index = candidate_index or get_candidate_index()

        # Cache for repeated queries to ensure 0 LLM calls on cache hit (Exit Criterion 6-D)
        self._query_cache: dict[str, tuple[SearchPlan, list[SearchHit], bool]] = {}

    def clear_cache(self) -> None:
        self._query_cache.clear()

    async def search(
        self,
        query: str,
        limit: int = 10,
    ) -> tuple[SearchPlan, list[SearchHit], bool]:
        """Execute talent search: plan query, invoke tools, re-rank with citations.

        Returns:
            (plan, ranked_hits, used_llm)
        """
        cache_key = f"{query.strip().lower()}::{limit}"
        if cache_key in self._query_cache:
            log.debug("search.cache_hit", query=query)
            return self._query_cache[cache_key]

        t0 = time.perf_counter()

        # 1. Planner (LLM call or deterministic fallback)
        plan, used_llm = await plan_search(query, self.llm, self.repo)

        # 2. Tool loop (up to 4 tool rounds per plan §6.4)
        # Round 1: Search skills to expand any remaining raw terms
        all_target_skills = list(plan.must_skills + plan.should_skills)
        if not all_target_skills:
            # Query might have general terms; try resolving with Tool 1
            expanded = search_skills(query, self.repo, self.skill_index, limit=3)
            plan.must_skills.extend(expanded)

        # Round 2: Tool 2 - Hard filtering
        hard_filtered_ids = filter_candidates(
            skill_ids=plan.must_skills,
            min_years=plan.min_years,
            domain=plan.domain,
            limit=50,
        )

        # Round 3: Tool 3 - Semantic candidate retrieval
        semantic_hits = semantic_candidates(
            text=query,
            candidate_index=self.candidate_index,
            k=max(limit * 2, 20),
        )
        semantic_ids = [h["candidate_id"] for h in semantic_hits]

        # Combine candidates (preserving order: hard-filtered first, then semantic)
        candidate_pool: list[str] = []
        for cid in hard_filtered_ids + semantic_ids:
            if cid not in candidate_pool:
                candidate_pool.append(cid)

        # Fallback if pool is empty: retrieve top semantic candidates
        if not candidate_pool and semantic_ids:
            candidate_pool = semantic_ids[:limit]

        # Round 4: Tool 4 - Match and score candidates against the plan
        evaluated_candidates: list[dict[str, Any]] = []
        for cid in candidate_pool:
            match_data = match_candidate(
                candidate_id=cid,
                plan=plan,
                repo=self.repo,
                skill_index=self.skill_index,
            )
            if match_data is not None:
                evaluated_candidates.append(match_data)

        # 3. Re-rank results by score descending
        evaluated_candidates.sort(key=lambda x: float(x["score"]), reverse=True)

        ranked_hits: list[SearchHit] = []
        for cand in evaluated_candidates[:limit]:
            ranked_hits.append(
                SearchHit(
                    candidate_id=cand["candidate_id"],
                    score=round(cand["score"], 4),
                    reasons=cand["reasons"],
                    citations=cand["citations"],
                    matched_skills=cand["matched_skills"],
                    missing_skills=cand["missing_skills"],
                )
            )

        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        log.info(
            "search.complete",
            query=query,
            hits=len(ranked_hits),
            used_llm=used_llm,
            latency_ms=elapsed_ms,
        )

        result = (plan, ranked_hits, used_llm)
        self._query_cache[cache_key] = result
        return result

    async def handle(self, msg: AgentMessage) -> AgentResult:
        """Handle incoming AgentMessage per Agent protocol."""
        query = msg.payload.get("query")
        if not query:
            return AgentResult(
                status="failed",
                data={"error": "Missing 'query' in payload"},
                quality=QualityScore(score=0.0),
                latency_ms=0,
            )

        limit = int(msg.payload.get("limit", 10))
        plan, hits, used_llm = await self.search(query, limit=limit)

        status_val = "ok" if used_llm else "partial"
        avg_score = sum(h.score for h in hits) / len(hits) if hits else 0.0

        return AgentResult(
            status=status_val,
            data={
                "plan": plan.model_dump(),
                "total_candidates": len(hits),
                "results": [h.model_dump() for h in hits],
            },
            quality=QualityScore(score=avg_score),
            latency_ms=0,
        )
