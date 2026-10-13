"""Phase 1.5: seed the taxonomy into PostgreSQL and the Chroma `skills` collection.

    uv run python scripts/seed.py --stats              # file stats + 1-A checks (exit 1 on fail)
    uv run python scripts/seed.py --taxonomy --stats   # also seed Postgres and Chroma

Seeding is idempotent: skills are upserted by slug (IDs stay stable for candidate_skills), skills
no longer in the files are deleted, and the derived tables (aliases, implications, relations) are
replaced. Every skill is embedded from its name, top 3 aliases and description and upserted into
Chroma; vectors for removed skills are deleted so the DB and Chroma counts stay equal (1-C).

Running natively against the compose stack needs localhost URLs, e.g.
    DATABASE_URL=postgresql+asyncpg://talentgraph:talentgraph@localhost:5432/talentgraph
    CHROMA_HOST=localhost CHROMA_PORT=8001
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import logging
import sys
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Any

import yaml

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("seed")

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data" / "taxonomy"
TAXONOMY_FILES = ("skills.csv", "aliases.csv", "implications.yaml", "relations.yaml")


def _chunks[T](items: Sequence[T], size: int) -> Iterator[Sequence[T]]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


def compute_taxonomy_version() -> str:
    """Deterministic SHA-256 (first 16 hex chars) over the four taxonomy files."""
    hasher = hashlib.sha256()
    for name in sorted(TAXONOMY_FILES):
        path = DATA_DIR / name
        if path.exists():
            # Normalize line endings so a git checkout with autocrlf hashes the same.
            hasher.update(path.read_bytes().replace(b"\r\n", b"\n"))
    return hasher.hexdigest()[:16]


def load_taxonomy_from_files() -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    """Load skills.csv, aliases.csv, implications.yaml and relations.yaml."""
    skills_file = DATA_DIR / "skills.csv"
    if not skills_file.exists():
        raise FileNotFoundError(f"Missing {skills_file}. Run scripts/build_taxonomy.py first.")

    with open(skills_file, encoding="utf-8") as f:
        skills = [
            {
                "slug": row["slug"],
                "name": row["name"],
                "type": row["type"],
                "level": int(row["level"]),
                "parent_slug": row["parent_slug"],
                "description": row["description"],
            }
            for row in csv.DictReader(f)
        ]

    with open(DATA_DIR / "aliases.csv", encoding="utf-8") as f:
        aliases = [
            {
                "slug": row["slug"],
                "alias": row["alias"],
                "alias_normalized": row["alias_normalized"],
                "ambiguous": row["ambiguous"].lower() in ("true", "1", "yes"),
                "source": row["source"],
            }
            for row in csv.DictReader(f)
        ]

    with open(DATA_DIR / "implications.yaml", encoding="utf-8") as f:
        implications: list[dict[str, Any]] = (yaml.safe_load(f) or {}).get("implications", [])
    with open(DATA_DIR / "relations.yaml", encoding="utf-8") as f:
        relations: list[dict[str, Any]] = (yaml.safe_load(f) or {}).get("relations", [])

    return skills, aliases, implications, relations


def verify_taxonomy_stats() -> bool:
    """Print taxonomy stats and return whether exit criterion 1-A passes."""
    skills, aliases, implications, relations = load_taxonomy_from_files()

    print("\n=================== TALENTGRAPH TAXONOMY STATS ===================")
    print(f"Taxonomy Version (Content Hash): {compute_taxonomy_version()}")
    print(f"Total Skills:                    {len(skills)}")
    print(f"Total Aliases:                   {len(aliases)}")
    print(f"Total Implication Rules:         {len(implications)}")
    print(f"Total Relation Edges:            {len(relations)}")

    level_counts: dict[int, int] = {}
    for s in skills:
        level_counts[s["level"]] = level_counts.get(s["level"], 0) + 1
    print("\nLevel Distribution:")
    for lvl in sorted(level_counts):
        print(f"  Level {lvl}: {level_counts[lvl]:5d} items")

    source_counts: dict[str, int] = {}
    for a in aliases:
        source_counts[a["source"]] = source_counts.get(a["source"], 0) + 1
    print("\nAlias Sources:")
    for src, n in sorted(source_counts.items()):
        print(f"  {src:10s} {n:6d}")

    roots = [s for s in skills if s["level"] == 0]
    print(f"\nRoot Domains ({len(roots)}):")
    for r in roots:
        print(f"  - {r['slug']} ({r['name']})")

    slug_map = {s["slug"]: s for s in skills}
    orphans = [
        s["slug"]
        for s in skills
        if s["level"] > 0
        and (
            s["parent_slug"] not in slug_map
            or slug_map[s["parent_slug"]]["level"] != s["level"] - 1
        )
    ]
    print(f"\nOrphan Skills (level > 0 without a valid level-1 parent): {len(orphans)}")

    has_cycle = False
    for s in skills:
        visited: set[str] = set()
        curr = s["slug"]
        while curr and curr in slug_map:
            if curr in visited:
                has_cycle = True
                print(f"Cycle detected at slug: {curr}")
                break
            visited.add(curr)
            curr = slug_map[curr]["parent_slug"]
        if has_cycle:
            break
    print(f"Hierarchy Cycle Check: {'FAILED (Cycles found)' if has_cycle else 'PASSED'}")

    passes = (
        len(skills) >= 5000
        and len(aliases) >= 15000
        and sorted(level_counts) == [0, 1, 2, 3]
        and not orphans
        and not has_cycle
    )
    print(f"\nExit criterion 1-A: {'PASS' if passes else 'FAIL'}")
    print("==================================================================\n")
    return passes


async def seed_database(
    skills: list[dict[str, Any]],
    aliases: list[dict[str, Any]],
    implications: list[dict[str, Any]],
    relations: list[dict[str, Any]],
    tax_ver: str,
) -> None:
    """Idempotent upsert of the taxonomy tables."""
    from sqlalchemy import delete, select
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from sqlalchemy.ext.asyncio import AsyncSession

    from talentgraph.db.models import Skill, SkillAlias, SkillImplication, SkillRelation
    from talentgraph.db.session import dispose_engine, init_engine

    engine = init_engine()
    try:
        async with AsyncSession(engine) as session, session.begin():
            slug_to_id: dict[str, int] = {}
            for level in sorted({s["level"] for s in skills}):
                rows = [
                    {
                        "slug": s["slug"],
                        "name": s["name"],
                        "type": s["type"],
                        "level": s["level"],
                        "parent_id": slug_to_id.get(s["parent_slug"]),
                        "description": s["description"],
                        "taxonomy_version": tax_ver,
                    }
                    for s in skills
                    if s["level"] == level
                ]
                for chunk in _chunks(rows, 1000):
                    stmt = pg_insert(Skill).values(list(chunk))
                    stmt = stmt.on_conflict_do_update(
                        index_elements=[Skill.slug],
                        set_={
                            col: stmt.excluded[col]
                            for col in (
                                "name",
                                "type",
                                "level",
                                "parent_id",
                                "description",
                                "taxonomy_version",
                            )
                        },
                    )
                    await session.execute(stmt)
                res = await session.execute(
                    select(Skill.slug, Skill.id).where(Skill.level == level)
                )
                slug_to_id.update({slug: id_ for slug, id_ in res.all()})

            # Derived tables are rebuilt from the files; nothing else references them.
            await session.execute(delete(SkillRelation))
            await session.execute(delete(SkillImplication))
            await session.execute(delete(SkillAlias))

            # Remove skills that left the taxonomy, deepest level first (parent FK).
            current = {s["slug"] for s in skills}
            stale = (await session.execute(select(Skill.slug, Skill.level))).all()
            for slug, _level in sorted(stale, key=lambda r: -r[1]):
                if slug not in current:
                    await session.execute(delete(Skill).where(Skill.slug == slug))
            if any(slug not in current for slug, _ in stale):
                logger.info("Deleted %d stale skills", sum(s not in current for s, _ in stale))

            alias_rows = [
                {
                    "skill_id": slug_to_id[a["slug"]],
                    "alias": a["alias"],
                    "alias_normalized": a["alias_normalized"],
                    "ambiguous": a["ambiguous"],
                    "source": a["source"],
                }
                for a in aliases
            ]
            for chunk in _chunks(alias_rows, 2000):
                await session.execute(pg_insert(SkillAlias).values(list(chunk)))

            imp_rows = [
                {
                    "antecedent_ids": [slug_to_id[s] for s in imp["antecedent_slugs"]],
                    "consequent_id": slug_to_id[imp["consequent_slug"]],
                    "min_count": int(imp.get("min_count", 1)),
                    "confidence": float(imp.get("confidence", 0.8)),
                }
                for imp in implications
            ]
            if imp_rows:
                await session.execute(pg_insert(SkillImplication).values(imp_rows))

            rel_rows: dict[tuple[int, int, str], dict[str, Any]] = {}
            for rel in relations:
                key = (
                    slug_to_id[rel["skill_slug"]],
                    slug_to_id[rel["related_slug"]],
                    rel.get("kind", "related"),
                )
                rel_rows[key] = {
                    "skill_id": key[0],
                    "related_id": key[1],
                    "kind": key[2],
                    "weight": float(rel.get("weight", 1.0)),
                }
            if rel_rows:
                await session.execute(pg_insert(SkillRelation).values(list(rel_rows.values())))

        logger.info(
            "Postgres: %d skills, %d aliases, %d implications, %d relations (version %s)",
            len(skills),
            len(alias_rows),
            len(imp_rows),
            len(rel_rows),
            tax_ver,
        )
    finally:
        await dispose_engine()


def seed_vectors(skills: list[dict[str, Any]], aliases: list[dict[str, Any]], tax_ver: str) -> None:
    """Embed every skill and upsert it into the Chroma `skills` collection."""
    from talentgraph.config import get_settings
    from talentgraph.embeddings.encoder import Encoder
    from talentgraph.embeddings.vector_store import ChromaVectorStore, Metadata

    settings = get_settings()
    store = ChromaVectorStore(settings.chroma_host, settings.chroma_port, "skills")

    slug_to_aliases: dict[str, list[str]] = {}
    for a in aliases:
        if a["alias_normalized"] != a["alias"].lower():  # prefer distinct-looking forms first
            slug_to_aliases.setdefault(a["slug"], []).append(a["alias"])
    for a in aliases:
        slug_to_aliases.setdefault(a["slug"], []).append(a["alias"])

    ids: list[str] = []
    texts: list[str] = []
    metas: list[Metadata] = []
    for s in skills:
        top = [x for x in dict.fromkeys(slug_to_aliases.get(s["slug"], [])) if x != s["name"]][:3]
        alias_text = f" (also known as {', '.join(top)})" if top else ""
        ids.append(s["slug"])
        texts.append(f"{s['name']}{alias_text}: {s['description']}")
        metas.append(
            {
                "type": s["type"],
                "level": s["level"],
                "parent_slug": s["parent_slug"],
                "taxonomy_version": tax_ver,
            }
        )

    logger.info("Encoding %d skills with %s...", len(texts), settings.embedding_model)
    vectors = Encoder.get().encode(texts, batch_size=128)
    for i in range(0, len(ids), 1000):
        store.upsert(ids[i : i + 1000], vectors[i : i + 1000], metas[i : i + 1000])

    stale = sorted(set(store.ids()) - set(ids))
    for chunk in _chunks(stale, 1000):
        store.delete(list(chunk))
    logger.info(
        "Chroma 'skills': %d vectors (%d stale removed), version %s",
        store.count(),
        len(stale),
        tax_ver,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed taxonomy into Postgres and ChromaDB")
    parser.add_argument(
        "--taxonomy", action="store_true", help="Seed taxonomy tables and vector collection"
    )
    parser.add_argument(
        "--stats", action="store_true", help="Print taxonomy statistics and verify integrity"
    )
    args = parser.parse_args()

    ok = True
    if args.stats or not args.taxonomy:
        ok = verify_taxonomy_stats()

    if args.taxonomy:
        skills, aliases, implications, relations = load_taxonomy_from_files()
        tax_ver = compute_taxonomy_version()
        logger.info("Taxonomy version: %s", tax_ver)
        asyncio.run(seed_database(skills, aliases, implications, relations, tax_ver))
        seed_vectors(skills, aliases, tax_ver)

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
