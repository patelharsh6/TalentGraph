"""Unit test verifying ORM models and Alembic migration alignment (plan §7.1)."""

from pathlib import Path

from talentgraph.db.models import Base


def test_orm_models_tables() -> None:
    expected_tables = {
        "skills",
        "skill_aliases",
        "skill_implications",
        "skill_relations",
        "emerging_skills",
        "candidates",
        "candidate_skills",
        "jobs",
        "matches",
        "batch_jobs",
        "batch_items",
        "agent_runs",
    }
    actual_tables = set(Base.metadata.tables.keys())
    assert expected_tables == actual_tables, (
        f"Mismatch in DB tables. Expected: {expected_tables}, got: {actual_tables}"
    )


def test_alembic_initial_migration_exists() -> None:
    migration_dir = Path(__file__).resolve().parent.parent.parent / "migrations" / "versions"
    migration_files = list(migration_dir.glob("*.py"))
    assert len(migration_files) >= 1, (
        "Initial Alembic migration script is missing in migrations/versions"
    )

    # Check that initial migration script has upgrade and downgrade functions
    initial_script = migration_files[0].read_text(encoding="utf-8")
    assert "def upgrade()" in initial_script
    assert "def downgrade()" in initial_script
