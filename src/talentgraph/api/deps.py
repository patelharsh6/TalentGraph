"""FastAPI dependencies (settings, DB session, API key check, agents)."""

from collections.abc import AsyncIterator
from typing import cast

from fastapi import Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from talentgraph.agents.coach.agent import CoachAgent
from talentgraph.agents.matching.agent import MatchingAgent
from talentgraph.agents.matching.job_parser import JobParser
from talentgraph.agents.normalization.agent import NormalizationAgent
from talentgraph.agents.parsing.agent import ParsingAgent
from talentgraph.agents.search.agent import SearchAgent
from talentgraph.config import Settings, get_settings
from talentgraph.db.repositories.taxonomy import (
    TaxonomyRepository,
    get_taxonomy_repository,
)
from talentgraph.db.session import get_session


def get_current_settings() -> Settings:
    """Dependency returning current application settings."""
    return get_settings()


async def get_db() -> AsyncIterator[AsyncSession]:
    """Dependency yielding an async SQLAlchemy session."""
    async for session in get_session():
        yield session


def get_redis(request: Request) -> Redis | None:
    """Dependency returning Redis client from app state if available."""
    return getattr(request.app.state, "redis", None)


def get_parsing_agent(request: Request) -> ParsingAgent:
    """Dependency returning ParsingAgent from app state or default instance."""
    agent = getattr(request.app.state, "parsing_agent", None)
    if agent is None:
        agent = ParsingAgent()
        request.app.state.parsing_agent = agent
    return cast(ParsingAgent, agent)


def get_normalization_agent(request: Request) -> NormalizationAgent:
    """Dependency returning NormalizationAgent from app state or default instance."""
    agent = getattr(request.app.state, "normalization_agent", None)
    if agent is None:
        agent = NormalizationAgent()
        request.app.state.normalization_agent = agent
    return cast(NormalizationAgent, agent)


def get_matching_agent(request: Request) -> MatchingAgent:
    """Dependency returning MatchingAgent from app state or default instance."""
    agent = getattr(request.app.state, "matching_agent", None)
    if agent is None:
        agent = MatchingAgent()
        request.app.state.matching_agent = agent
    return cast(MatchingAgent, agent)


def get_job_parser(request: Request) -> JobParser:
    """Dependency returning JobParser from app state or default instance."""
    agent = getattr(request.app.state, "job_parser", None)
    if agent is None:
        agent = JobParser()
        request.app.state.job_parser = agent
    return cast(JobParser, agent)


def get_taxonomy_repo(request: Request) -> TaxonomyRepository:
    """Dependency returning TaxonomyRepository from app state or default repository."""
    repo = getattr(request.app.state, "taxonomy_repo", None)
    if repo is None:
        repo = get_taxonomy_repository()
        request.app.state.taxonomy_repo = repo
    return cast(TaxonomyRepository, repo)


def get_search_agent(request: Request) -> SearchAgent:
    """Dependency returning SearchAgent from app state or default instance."""
    agent = getattr(request.app.state, "search_agent", None)
    if agent is None:
        agent = SearchAgent()
        request.app.state.search_agent = agent
    return cast(SearchAgent, agent)


def get_coach_agent(request: Request) -> CoachAgent:
    """Dependency returning CoachAgent from app state or default instance."""
    agent = getattr(request.app.state, "coach_agent", None)
    if agent is None:
        agent = CoachAgent()
        request.app.state.coach_agent = agent
    return cast(CoachAgent, agent)
