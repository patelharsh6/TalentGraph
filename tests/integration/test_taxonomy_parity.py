"""Exit criterion 1-C: Postgres `skills` and the Chroma `skills` collection hold the same taxonomy.

Needs the compose stack and a seeded taxonomy:
    docker compose up -d
    uv run python scripts/seed.py --taxonomy
    uv run pytest -m integration
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import create_async_engine

from talentgraph.config import get_settings
from talentgraph.db.models import Skill, SkillAlias
from talentgraph.embeddings.vector_store import ChromaVectorStore

pytestmark = pytest.mark.integration

ROOT_DIR = Path(__file__).resolve().parent.parent.parent


def _file_taxonomy_version() -> str:
    spec = importlib.util.spec_from_file_location("seed", ROOT_DIR / "scripts" / "seed.py")
    assert spec and spec.loader
    seed = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(seed)
    version: str = seed.compute_taxonomy_version()
    return version


async def test_db_and_vector_counts_match_and_version_is_current() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    try:
        async with engine.connect() as conn:
            n_skills = (await conn.execute(select(func.count()).select_from(Skill))).scalar_one()
            n_aliases = (
                await conn.execute(select(func.count()).select_from(SkillAlias))
            ).scalar_one()
            versions = set(
                (await conn.execute(select(Skill.taxonomy_version).distinct())).scalars()
            )
    finally:
        await engine.dispose()

    store = ChromaVectorStore(settings.chroma_host, settings.chroma_port, "skills")
    expected_version = _file_taxonomy_version()

    assert n_skills >= 5000
    assert n_aliases >= 15000
    assert store.count() == n_skills
    assert versions == {expected_version}
    # Metadata via the chromadb client: no encoder needed (torch is unavailable on some hosts).
    import chromadb

    sample = (
        chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)
        .get_collection("skills")
        .get(limit=50, include=["metadatas"])
    )
    assert sample["ids"], "Chroma 'skills' collection is empty"
    assert {m["taxonomy_version"] for m in sample["metadatas"]} == {expected_version}
