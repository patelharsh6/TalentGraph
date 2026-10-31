"""Step 4.1: job description to JobRequirements (Gemini, cached by hash, normalized skills)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

import structlog

from talentgraph import PIPELINE_VERSION
from talentgraph.agents.normalization.cascade import SkillCascade
from talentgraph.config import Settings, get_settings
from talentgraph.core.ids import sha256_hex
from talentgraph.core.schemas.matching import (
    JobRequirement,
    JobRequirements,
    RawJobExtraction,
)
from talentgraph.llm.client import LLMClient, get_llm

if TYPE_CHECKING:
    from redis.asyncio import Redis

log = structlog.get_logger(__name__)

PROMPT_PATH = (
    Path(__file__).resolve().parent.parent.parent / "llm" / "prompts" / "job_extraction.md"
)


def jd_cache_key(sha256: str) -> str:
    return f"jd:{sha256}:{PIPELINE_VERSION}"


class JDCache(Protocol):
    async def get(self, sha256: str) -> JobRequirements | None: ...

    async def set(self, sha256: str, result: JobRequirements) -> None: ...


class InMemoryJDCache:
    """In-memory cache for unit tests and local execution."""

    def __init__(self) -> None:
        self._data: dict[str, str] = {}

    async def get(self, sha256: str) -> JobRequirements | None:
        raw = self._data.get(jd_cache_key(sha256))
        return JobRequirements.model_validate_json(raw) if raw else None

    async def set(self, sha256: str, result: JobRequirements) -> None:
        self._data[jd_cache_key(sha256)] = result.model_dump_json()


class RedisJDCache:
    """Redis-backed cache with 7-day TTL."""

    def __init__(self, redis: Redis, *, ttl_s: int = 7 * 86400) -> None:
        self._redis = redis
        self._ttl_s = ttl_s

    async def get(self, sha256: str) -> JobRequirements | None:
        try:
            raw = await self._redis.get(jd_cache_key(sha256))
        except Exception as exc:
            log.warning("jd_cache.get_failed", error=str(exc))
            return None
        return JobRequirements.model_validate_json(raw) if raw else None

    async def set(self, sha256: str, result: JobRequirements) -> None:
        try:
            await self._redis.set(
                jd_cache_key(sha256),
                result.model_dump_json(),
                ex=self._ttl_s,
            )
        except Exception as exc:
            log.warning("jd_cache.set_failed", error=str(exc))


def _slugify(text: str) -> str:
    s = text.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


class JobParser:
    """Extracts and normalizes structured JobRequirements from JD text."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        llm: LLMClient | None = None,
        cascade: SkillCascade | None = None,
        cache: JDCache | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._llm = llm if llm is not None else get_llm(self._settings)
        self._cascade = cascade
        self._cache = cache
        self._prompt: str | None = None

    def _get_system_prompt(self) -> str:
        if self._prompt is None:
            if PROMPT_PATH.is_file():
                self._prompt = PROMPT_PATH.read_text(encoding="utf-8")
            else:
                self._prompt = "Extract job title, company, requirements, and seniority."
        return self._prompt

    async def parse(self, text: str, *, job_id: str | None = None) -> JobRequirements:
        """Parse raw job description text into normalized JobRequirements."""
        if not text.strip():
            return JobRequirements(schema_version="1.0", job_id=job_id, raw_text_length=0)

        sha = sha256_hex(text)
        if self._cache is not None:
            cached = await self._cache.get(sha)
            if cached is not None:
                if job_id and not cached.job_id:
                    cached.job_id = job_id
                return cached

        system_prompt = self._get_system_prompt()
        raw_extraction = await self._llm.extract(RawJobExtraction, system_prompt, text)

        req_map: dict[str, JobRequirement] = {}
        for raw_req in raw_extraction.requirements:
            norm_slug: str | None = None
            norm_name: str | None = None

            if self._cascade is not None:
                cascade_res = await self._cascade.normalize_one(raw_req.name, context=text[:500])
                for cr in cascade_res:
                    if cr.canonical is not None:
                        norm_slug = cr.canonical.slug
                        norm_name = cr.canonical.name
                        break
                    elif cr.candidate_text:
                        norm_slug = _slugify(cr.candidate_text)
                        norm_name = cr.candidate_text

            if not norm_slug:
                norm_slug = _slugify(raw_req.name)
                norm_name = raw_req.name

            # Deduplicate by slug, keeping highest importance and min_years
            if norm_slug in req_map:
                existing = req_map[norm_slug]
                max_imp = max(existing.importance, raw_req.importance)
                req_val = existing.required or raw_req.required
                years = existing.min_years
                if raw_req.min_years is not None:
                    years = (
                        max(years, raw_req.min_years)
                        if years is not None
                        else raw_req.min_years
                    )
                req_map[norm_slug] = JobRequirement(
                    skill_slug=norm_slug,
                    name=norm_name or existing.name,
                    required=req_val,
                    importance=max_imp,
                    min_years=years,
                )
            else:
                req_map[norm_slug] = JobRequirement(
                    skill_slug=norm_slug,
                    name=norm_name or raw_req.name,
                    required=raw_req.required,
                    importance=raw_req.importance,
                    min_years=raw_req.min_years,
                )

        parsed = JobRequirements(
            schema_version="1.0",
            job_id=job_id,
            title=raw_extraction.title,
            company=raw_extraction.company,
            seniority=raw_extraction.seniority,
            role_family=raw_extraction.role_family,
            min_total_experience_years=raw_extraction.min_total_experience_years,
            education=raw_extraction.education,
            requirements=list(req_map.values()),
            raw_text_length=len(text),
        )

        if self._cache is not None:
            await self._cache.set(sha, parsed)

        return parsed

    @classmethod
    def load_from_ground_truth(cls, path_or_id: str | Path) -> JobRequirements:
        """Load JobRequirements from an existing ground truth file or ID."""
        p = Path(path_or_id)
        if not p.is_file():
            # Try finding in data/jobs/
            root = Path(__file__).resolve().parents[4]
            p = root / "data" / "jobs" / f"{path_or_id}.gt.json"

        if not p.is_file():
            raise FileNotFoundError(f"Job ground truth file not found: {path_or_id}")

        data = json.loads(p.read_text(encoding="utf-8"))
        job_id = p.stem.replace(".gt", "")
        reqs = [
            JobRequirement(
                skill_slug=r["skill_slug"],
                name=r.get("skill_name", r["skill_slug"]),
                required=r.get("required", True),
                importance=r.get("importance", 3),
                min_years=r.get("min_years"),
            )
            for r in data.get("requirements", [])
        ]
        return JobRequirements(
            schema_version="1.0",
            job_id=job_id,
            title=data.get("title", ""),
            company=data.get("company"),
            seniority=data.get("seniority"),
            role_family=data.get("role_family"),
            min_total_experience_years=data.get("min_total_experience_years"),
            education=data.get("education", []),
            requirements=reqs,
            raw_text_length=data.get("raw_text_length", 0),
        )
