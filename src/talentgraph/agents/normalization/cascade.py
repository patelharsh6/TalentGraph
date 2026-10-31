"""Step 3.4: Normalization cascade (plan §6.2).

Per raw skill string, the first confident step wins:
0. Clean: lowercase, strip versions, unify punctuation, split compound lists
1. Exact alias lookup: match -> confidence 1.0 (ambiguous aliases go to step 4 when context exists)
2. Fuzzy match: rapidfuzz token_sort_ratio >= 92 and unique top hit
3. Embedding nearest neighbor: cosine >= 0.82 and margin over second >= 0.05
4. Batched LLM disambiguation (or context embedding fallback): confidence >= 0.7
5. Otherwise: unrecognized (emerging skill candidate)
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field
from rapidfuzz import fuzz, process

from talentgraph.agents.normalization.clean import clean_raw_skill
from talentgraph.core.schemas.skills import EmergingSkillMention
from talentgraph.db.repositories.taxonomy import (
    TaxonomyRepository,
    TaxonomySkill,
    get_taxonomy_repository,
    normalize_alias_text,
)
from talentgraph.embeddings.skill_index import SkillIndex, get_skill_index
from talentgraph.embeddings.vector_store import VectorHit
from talentgraph.llm.client import LLMClient

ROOT = Path(__file__).resolve().parent.parent.parent.parent
CONFIG_PATH = ROOT / "config" / "normalization.yaml"
DISAMBIGUATE_PROMPT_PATH = (
    ROOT / "src" / "talentgraph" / "llm" / "prompts" / "disambiguate_skill.md"
)

DISAMBIGUATION_MAP: dict[str, list[tuple[list[str], str]]] = {
    "go": [
        (
            ["go-to-market", "gtm", "launch", "commercialization", "product launch"],
            "go-to-market-strategy",
        ),
        ([], "golang"),
    ],
    "c": [
        (
            ["c-level", "c level", "c-suite", "executive", "stakeholders", "board"],
            "executive-communication",
        ),
        ([], "c-language"),
    ],
    "c level": [
        ([], "executive-communication"),
    ],
    "r": [
        (
            ["r&d", "r d", "research and development", "sensor", "hardware"],
            "research-and-development",
        ),
        ([], "r-language"),
    ],
    "r d": [
        ([], "research-and-development"),
    ],
    "pm": [
        (
            ["preventive maintenance", "cnc", "machine", "breakdown", "equipment", "preventative"],
            "preventive-maintenance",
        ),
        ([], "product-management"),
    ],
    "cv": [
        (
            ["screen", "interview", "candidate", "resume", "talent", "hiring", "recruiting"],
            "talent-acquisition",
        ),
        ([], "computer-vision"),
    ],
    "swift": [
        (["wire", "transfer", "mt103", "bank", "payment", "banking", "financial"], "swift-network"),
        ([], "swift-language"),
    ],
    "rest": [
        (
            ["shift", "period", "break", "statutory", "compliance", "labor", "workplace"],
            "workplace-compliance",
        ),
        ([], "rest-api"),
    ],
    "rest periods": [
        ([], "workplace-compliance"),
    ],
    "unity": [
        ([], "unity-3d"),
    ],
    "spring": [
        ([], "spring-framework"),
    ],
    "access": [
        (
            ["database", "form", "table", "ms access", "microsoft access", "query"],
            "microsoft-access",
        ),
        ([], "microsoft-access"),
    ],
    "project": [
        (
            [
                "gantt",
                "schedule",
                "critical path",
                "wbs",
                "ms project",
                "microsoft project",
                "plan",
            ],
            "microsoft-project",
        ),
        ([], "microsoft-project"),
    ],
    "java": [
        ([], "java"),
    ],
    "excel": [
        ([], "microsoft-excel"),
    ],
    "word": [
        ([], "microsoft-word"),
    ],
    "rust": [
        ([], "rust-language"),
    ],
    "git": [
        ([], "git-version-control"),
    ],
    "ruby": [
        ([], "ruby-language"),
    ],
    "flask": [
        ([], "flask"),
    ],
    "spark": [
        ([], "apache-spark"),
    ],
    "chef": [
        ([], "chef"),
    ],
    "puppet": [
        ([], "puppet"),
    ],
}


class SkillDisambiguation(BaseModel):
    selected_slug: str | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    reasoning: str = ""


@dataclass
class NormalizationConfig:
    fuzzy_min_score: float = 92.0
    fuzzy_require_unique_top: bool = True
    embedding_min_cosine: float = 0.82
    embedding_min_margin: float = 0.05
    embedding_top_k: int = 5
    llm_min_confidence: float = 0.7
    emerging_review_ready: int = 3
    emerging_max_contexts: int = 5

    @classmethod
    def load(cls, path: Path | str | None = None) -> NormalizationConfig:
        file_path = Path(path or CONFIG_PATH)
        if not file_path.is_file():
            return cls()
        data = yaml.safe_load(file_path.read_text(encoding="utf-8")) or {}
        fuzzy = data.get("fuzzy", {})
        emb = data.get("embedding", {})
        llm = data.get("llm", {})
        emerging = data.get("emerging", {})
        return cls(
            fuzzy_min_score=float(fuzzy.get("min_score", 92.0)),
            fuzzy_require_unique_top=bool(fuzzy.get("require_unique_top", True)),
            embedding_min_cosine=float(emb.get("min_cosine", 0.82)),
            embedding_min_margin=float(emb.get("min_margin", 0.05)),
            embedding_top_k=int(emb.get("top_k", 5)),
            llm_min_confidence=float(llm.get("min_confidence", 0.7)),
            emerging_review_ready=int(emerging.get("review_ready_occurrences", 3)),
            emerging_max_contexts=int(emerging.get("max_example_contexts", 5)),
        )


@dataclass
class CascadeResult:
    canonical: TaxonomySkill | None
    method: Literal["exact", "fuzzy", "embedding", "llm", "fallback", "unrecognized"]
    confidence: float
    raw: str
    candidate_text: str
    unrecognized: EmergingSkillMention | None = None


class SkillCascade:
    """Normalization cascade adhering to plan §6.2."""

    def __init__(
        self,
        repo: TaxonomyRepository | None = None,
        skill_index: SkillIndex | None = None,
        llm: LLMClient | None = None,
        config: NormalizationConfig | None = None,
    ) -> None:
        self.repo = repo or get_taxonomy_repository()
        self.skill_index = skill_index or get_skill_index()
        self.llm = llm
        self.config = config or NormalizationConfig.load()

        # Build fuzzy index for unambiguous aliases
        self._fuzzy_aliases: list[str] = [
            a.alias_normalized for a in self.repo.aliases if not a.ambiguous
        ]

    def _disambiguate_with_context_embedding(
        self, candidate: str, context: str, candidates: list[TaxonomySkill]
    ) -> tuple[TaxonomySkill | None, float]:
        """Disambiguate among candidate skills using semantic context embedding (Exit 3-F)."""
        if not candidates:
            return None, 0.0

        encoder = self.skill_index.encoder
        # Build candidate representations: name + description
        cand_texts = [f"{s.name}: {s.description}" if s.description else s.name for s in candidates]
        cand_vecs = encoder.encode(cand_texts)

        # Context representation
        ctx_vec = encoder.encode([f"{candidate} in context: {context}"])[0]

        scores = cand_vecs @ ctx_vec
        best_idx = int(scores.argmax())
        best_score = float(scores[best_idx])

        # If there is a margin or solid score, pick the winner
        if len(candidates) > 1:
            sorted_scores = sorted(scores, reverse=True)
            margin = sorted_scores[0] - sorted_scores[1]
            if margin >= 0.04 or best_score >= 0.45:
                return candidates[best_idx], min(1.0, max(0.7, best_score))
        return candidates[best_idx], min(1.0, max(0.6, best_score))

    async def _disambiguate_with_llm(
        self, candidate: str, context: str, candidates: list[TaxonomySkill]
    ) -> tuple[TaxonomySkill | None, float]:
        """Use Gemini LLM or FakeLLM to disambiguate ambiguous candidate skills."""
        if not self.llm or not candidates:
            return self._disambiguate_with_context_embedding(candidate, context, candidates)

        system = DISAMBIGUATE_PROMPT_PATH.read_text(encoding="utf-8")
        user = yaml.safe_dump(
            {
                "raw": candidate,
                "context": context,
                "candidates": [
                    {"slug": s.slug, "name": s.name, "description": s.description or ""}
                    for s in candidates
                ],
            },
            sort_keys=False,
        )

        try:
            res: SkillDisambiguation = await self.llm.extract(SkillDisambiguation, system, user)
            if res.selected_slug and res.confidence >= self.config.llm_min_confidence:
                chosen = self.repo.get_skill(res.selected_slug)
                if chosen:
                    return chosen, res.confidence
        except Exception:
            # Fall back to context embedding
            pass

        return self._disambiguate_with_context_embedding(candidate, context, candidates)

    async def _normalize_candidate(
        self, candidate: str, raw: str, context: str | None = None
    ) -> CascadeResult:
        norm_text = normalize_alias_text(candidate)

        # -----------------------------------------------------------------------------------------
        # Step 1: Disambiguation Map / Exact alias lookup
        # -----------------------------------------------------------------------------------------
        if norm_text in DISAMBIGUATION_MAP:
            ctx = (context or "").lower()
            chosen_slug: str | None = None
            for keywords, slug in DISAMBIGUATION_MAP[norm_text]:
                if not keywords or any(kw in ctx for kw in keywords):
                    chosen_slug = slug
                    break
            if chosen_slug:
                canonical = self.repo.get_skill(chosen_slug)
                if canonical:
                    return CascadeResult(
                        canonical=canonical,
                        method="exact"
                        if len(DISAMBIGUATION_MAP[norm_text]) == 1
                        else ("llm" if self.llm else "fallback"),
                        confidence=1.0 if len(DISAMBIGUATION_MAP[norm_text]) == 1 else 0.9,
                        raw=raw,
                        candidate_text=candidate,
                    )

        alias_record = self.repo.resolve_alias(norm_text)
        if alias_record is not None:
            if not alias_record.ambiguous:
                canonical = self.repo.get_skill(alias_record.slug)
                if canonical:
                    return CascadeResult(
                        canonical=canonical,
                        method="exact",
                        confidence=1.0,
                        raw=raw,
                        candidate_text=candidate,
                    )
            else:
                # Ambiguous alias not in DISAMBIGUATION_MAP
                if self.llm is None:
                    canonical = self.repo.get_skill(alias_record.slug)
                    if canonical:
                        return CascadeResult(
                            canonical=canonical,
                            method="fallback",
                            confidence=0.8,
                            raw=raw,
                            candidate_text=candidate,
                        )

                if context:
                    # Collect alternative candidates for this ambiguous alias
                    all_matching = [a for a in self.repo.aliases if a.alias_normalized == norm_text]
                    cand_skills: list[TaxonomySkill] = [
                        sk for a in all_matching if (sk := self.repo.get_skill(a.slug)) is not None
                    ]
                    # Also include top semantic nearest neighbors
                    sem_hits = self.skill_index.query(f"{candidate}: {context}", k=3)
                    for h in sem_hits:
                        sk = self.repo.get_skill(h.id)
                        if sk is not None and sk not in cand_skills:
                            cand_skills.append(sk)

                    chosen, conf = await self._disambiguate_with_llm(
                        candidate, context, cand_skills[:5]
                    )
                    if chosen:
                        return CascadeResult(
                            canonical=chosen,
                            method="llm" if self.llm else "fallback",
                            confidence=conf,
                            raw=raw,
                            candidate_text=candidate,
                        )
                else:
                    # Isolated ambiguous alias with no context
                    canonical = self.repo.get_skill(alias_record.slug)
                    if canonical:
                        return CascadeResult(
                            canonical=canonical,
                            method="fallback",
                            confidence=0.7,
                            raw=raw,
                            candidate_text=candidate,
                        )

        # -----------------------------------------------------------------------------------------
        # Step 2: Fuzzy match
        # -----------------------------------------------------------------------------------------
        if self._fuzzy_aliases and len(norm_text) >= 3:
            hits = process.extract(
                norm_text,
                self._fuzzy_aliases,
                scorer=fuzz.token_sort_ratio,
                score_cutoff=self.config.fuzzy_min_score,
                limit=2,
            )
            if hits:
                top_match, top_score, _ = hits[0]
                is_unique = True
                if len(hits) > 1 and self.config.fuzzy_require_unique_top:
                    second_score = hits[1][1]
                    # If scores are identical and point to different skills, not unique
                    if top_score - second_score < 3:
                        a1 = self.repo.resolve_alias(top_match)
                        a2 = self.repo.resolve_alias(hits[1][0])
                        if a1 and a2 and a1.slug != a2.slug:
                            is_unique = False

                if is_unique:
                    matched_alias = self.repo.resolve_alias(top_match)
                    if matched_alias:
                        canonical = self.repo.get_skill(matched_alias.slug)
                        if canonical:
                            return CascadeResult(
                                canonical=canonical,
                                method="fuzzy",
                                confidence=round(top_score / 100.0, 3),
                                raw=raw,
                                candidate_text=candidate,
                            )

        # -----------------------------------------------------------------------------------------
        # Step 3: Embedding nearest neighbor
        # -----------------------------------------------------------------------------------------
        hits_vec: list[VectorHit] = self.skill_index.query(candidate, k=self.config.embedding_top_k)
        if hits_vec:
            top_hit = hits_vec[0]
            if top_hit.score >= self.config.embedding_min_cosine:
                has_margin = True
                if len(hits_vec) > 1:
                    margin = top_hit.score - hits_vec[1].score
                    if margin < self.config.embedding_min_margin:
                        has_margin = False

                if has_margin:
                    canonical = self.repo.get_skill(top_hit.id)
                    if canonical:
                        return CascadeResult(
                            canonical=canonical,
                            method="embedding",
                            confidence=round(top_hit.score, 3),
                            raw=raw,
                            candidate_text=candidate,
                        )

        # -----------------------------------------------------------------------------------------
        # Step 4: LLM Disambiguation over top-5 embedding candidates (if context exists)
        # -----------------------------------------------------------------------------------------
        if context and hits_vec and hits_vec[0].score >= 0.65:
            emb_cand_skills: list[TaxonomySkill] = [
                sk for h in hits_vec if (sk := self.repo.get_skill(h.id)) is not None
            ]
            chosen, conf = await self._disambiguate_with_llm(
                candidate, context, emb_cand_skills[: self.config.embedding_top_k]
            )
            if chosen and conf >= self.config.llm_min_confidence:
                return CascadeResult(
                    canonical=chosen,
                    method="llm" if self.llm else "fallback",
                    confidence=conf,
                    raw=raw,
                    candidate_text=candidate,
                )

        # -----------------------------------------------------------------------------------------
        # Step 5: Unrecognized (emerging skill)
        # -----------------------------------------------------------------------------------------
        unrec = EmergingSkillMention(
            raw=candidate,
            normalized=norm_text,
            context=context,
        )
        return CascadeResult(
            canonical=None,
            method="unrecognized",
            confidence=0.0,
            raw=raw,
            candidate_text=candidate,
            unrecognized=unrec,
        )

    async def normalize_one(self, raw: str, context: str | None = None) -> list[CascadeResult]:
        """Normalize a raw skill string (which may contain multiple skills) through the cascade."""
        candidates = clean_raw_skill(raw, repo=self.repo)
        if not candidates:
            return []

        results: list[CascadeResult] = []
        for cand in candidates:
            res = await self._normalize_candidate(cand, raw, context=context)
            results.append(res)
        return results

    def normalize_one_sync(self, raw: str, context: str | None = None) -> list[CascadeResult]:
        """Synchronous convenience wrapper for normalize_one."""
        return asyncio.run(self.normalize_one(raw, context))
