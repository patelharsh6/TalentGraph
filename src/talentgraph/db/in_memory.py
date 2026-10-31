"""In-memory data store for offline tests and running without Postgres."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from talentgraph.core.schemas.matching import JobRequirements, MatchResult
from talentgraph.core.schemas.resume import ParsedResume
from talentgraph.core.schemas.skills import SkillProfile


class InMemoryCandidateRecord:
    def __init__(
        self,
        candidate_id: UUID,
        file_sha256: str,
        parsed: ParsedResume,
        profile: SkillProfile,
        quality: float | None = None,
    ) -> None:
        self.id = candidate_id
        self.file_sha256 = file_sha256
        self.parsed = parsed
        self.profile = profile
        self.quality = quality


class InMemoryJobRecord:
    def __init__(
        self,
        job_id: UUID,
        title: str,
        raw_text: str,
        requirements: JobRequirements,
        text_sha256: str,
    ) -> None:
        self.id = job_id
        self.title = title
        self.raw_text = raw_text
        self.requirements = requirements
        self.text_sha256 = text_sha256


class InMemoryMatchRecord:
    def __init__(
        self,
        match_id: UUID,
        candidate_id: UUID,
        job_id: UUID,
        result: MatchResult,
        blind: bool = False,
    ) -> None:
        self.id = match_id
        self.candidate_id = candidate_id
        self.job_id = job_id
        self.result = result
        self.blind = blind


_CANDIDATES: dict[UUID, InMemoryCandidateRecord] = {}
_JOBS: dict[UUID, InMemoryJobRecord] = {}
_MATCHES: dict[UUID, InMemoryMatchRecord] = {}


def save_candidate_in_memory(record: InMemoryCandidateRecord) -> None:
    _CANDIDATES[record.id] = record


def get_candidate_in_memory(candidate_id: UUID) -> InMemoryCandidateRecord | None:
    return _CANDIDATES.get(candidate_id)


def get_all_candidates_in_memory() -> list[InMemoryCandidateRecord]:
    return list(_CANDIDATES.values())


def save_job_in_memory(record: InMemoryJobRecord) -> None:
    _JOBS[record.id] = record


def get_job_in_memory(job_id: UUID) -> InMemoryJobRecord | None:
    return _JOBS.get(job_id)


def save_match_in_memory(record: InMemoryMatchRecord) -> None:
    _MATCHES[record.id] = record


def get_match_in_memory(match_id: UUID) -> InMemoryMatchRecord | None:
    return _MATCHES.get(match_id)
