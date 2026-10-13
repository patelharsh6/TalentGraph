"""Initial schema creation for TalentGraph database tables.

Revision ID: 0001_initial_schema
Revises: None
Create Date: 2026-10-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Taxonomy: skills
    op.create_table(
        "skills",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("slug", sa.String(length=200), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("level", sa.SmallInteger(), nullable=False),
        sa.Column("parent_id", sa.Integer(), sa.ForeignKey("skills.id"), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("taxonomy_version", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_skills_slug", "skills", ["slug"], unique=True)
    op.create_index("ix_skills_parent_id", "skills", ["parent_id"], unique=False)

    # 2. Taxonomy: skill_aliases
    op.create_table(
        "skill_aliases",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "skill_id",
            sa.Integer(),
            sa.ForeignKey("skills.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("alias", sa.String(length=200), nullable=False),
        sa.Column("alias_normalized", sa.String(length=200), nullable=False),
        sa.Column("ambiguous", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
    )
    op.create_index("ix_skill_aliases_skill_id", "skill_aliases", ["skill_id"], unique=False)
    op.create_index(
        "ix_skill_aliases_alias_normalized", "skill_aliases", ["alias_normalized"], unique=True
    )

    # 3. Taxonomy: skill_implications
    op.create_table(
        "skill_implications",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("antecedent_ids", sa.ARRAY(sa.Integer()), nullable=False),
        sa.Column(
            "consequent_id",
            sa.Integer(),
            sa.ForeignKey("skills.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("min_count", sa.SmallInteger(), server_default=sa.text("1"), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
    )

    # 4. Taxonomy: skill_relations
    op.create_table(
        "skill_relations",
        sa.Column(
            "skill_id",
            sa.Integer(),
            sa.ForeignKey("skills.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "related_id",
            sa.Integer(),
            sa.ForeignKey("skills.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("kind", sa.String(length=20), primary_key=True),
        sa.Column("weight", sa.Float(), server_default=sa.text("1.0"), nullable=False),
    )

    # 5. Taxonomy: emerging_skills
    op.create_table(
        "emerging_skills",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("normalized_text", sa.String(length=200), nullable=False),
        sa.Column("occurrences", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column(
            "example_contexts",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column("merged_into", sa.Integer(), sa.ForeignKey("skills.id"), nullable=True),
        sa.Column("reviewed_by", sa.String(length=100), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_emerging_skills_normalized_text", "emerging_skills", ["normalized_text"], unique=True
    )

    # 6. Access: api_keys
    op.create_table(
        "api_keys",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("key_prefix", sa.String(length=16), nullable=False),
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("owner", sa.String(length=200), nullable=False),
        sa.Column("scopes", sa.ARRAY(sa.String(length=20)), nullable=False),
        sa.Column("rate_limit_per_min", sa.Integer(), server_default=sa.text("60"), nullable=False),
        sa.Column("webhook_secret", sa.String(length=64), nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_api_keys_key_prefix", "api_keys", ["key_prefix"], unique=False)
    op.create_index("ix_api_keys_key_hash", "api_keys", ["key_hash"], unique=True)

    # 7. Candidates
    op.create_table(
        "candidates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("api_key_id", sa.Integer(), sa.ForeignKey("api_keys.id"), nullable=False),
        sa.Column("file_sha256", sa.String(length=64), nullable=False),
        sa.Column("parsed", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("quality", sa.Float(), nullable=True),
        sa.Column("pipeline_version", sa.String(length=16), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_candidates_api_key_id", "candidates", ["api_key_id"], unique=False)
    op.create_index("ix_candidates_file_sha256", "candidates", ["file_sha256"], unique=False)

    # 8. Candidate Skills
    op.create_table(
        "candidate_skills",
        sa.Column(
            "candidate_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("candidates.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("skill_id", sa.Integer(), sa.ForeignKey("skills.id"), primary_key=True),
        sa.Column("proficiency", sa.SmallInteger(), nullable=False),
        sa.Column("years", sa.Float(), nullable=True),
        sa.Column("inferred", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column(
            "evidence",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )

    # 9. Jobs
    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("api_key_id", sa.Integer(), sa.ForeignKey("api_keys.id"), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("requirements", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("text_sha256", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_jobs_api_key_id", "jobs", ["api_key_id"], unique=False)
    op.create_index("ix_jobs_text_sha256", "jobs", ["text_sha256"], unique=False)

    # 10. Matches
    op.create_table(
        "matches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "candidate_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("candidates.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("threshold", sa.Float(), nullable=False),
        sa.Column("is_match", sa.Boolean(), nullable=False),
        sa.Column("breakdown", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("gaps", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_matches_candidate_id", "matches", ["candidate_id"], unique=False)
    op.create_index("ix_matches_job_id", "matches", ["job_id"], unique=False)

    # 11. Batch Jobs
    op.create_table(
        "batch_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("api_key_id", sa.Integer(), sa.ForeignKey("api_keys.id"), nullable=False),
        sa.Column(
            "status",
            sa.String(length=30),
            server_default=sa.text("'queued'"),
            nullable=False,
        ),
        sa.Column("total", sa.Integer(), nullable=False),
        sa.Column("succeeded", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("failed", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("partial", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("callback_url", sa.String(length=2000), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_batch_jobs_api_key_id", "batch_jobs", ["api_key_id"], unique=False)

    # 12. Batch Items
    op.create_table(
        "batch_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "batch_job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("batch_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("filename", sa.String(length=500), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default=sa.text("'queued'"),
            nullable=False,
        ),
        sa.Column(
            "candidate_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("candidates.id"),
            nullable=True,
        ),
        sa.Column("error", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.create_index("ix_batch_items_batch_job_id", "batch_items", ["batch_job_id"], unique=False)

    # 13. Webhook Deliveries
    op.create_table(
        "webhook_deliveries",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "batch_job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("batch_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("url", sa.String(length=2000), nullable=False),
        sa.Column("attempt", sa.SmallInteger(), nullable=False),
        sa.Column("status_code", sa.SmallInteger(), nullable=True),
        sa.Column("response_ms", sa.Integer(), nullable=True),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_webhook_deliveries_batch_job_id", "webhook_deliveries", ["batch_job_id"], unique=False
    )

    # 14. Observability: Agent Run Records
    op.create_table(
        "agent_runs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("trace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent", sa.String(length=20), nullable=False),
        sa.Column("attempt", sa.SmallInteger(), nullable=False),
        sa.Column("status", sa.String(length=10), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("quality", sa.Float(), nullable=True),
        sa.Column("error_code", sa.String(length=50), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_agent_runs_trace_id", "agent_runs", ["trace_id"], unique=False)


def downgrade() -> None:
    op.drop_table("agent_runs")
    op.drop_table("webhook_deliveries")
    op.drop_table("batch_items")
    op.drop_table("batch_jobs")
    op.drop_table("matches")
    op.drop_table("jobs")
    op.drop_table("candidate_skills")
    op.drop_table("candidates")
    op.drop_table("api_keys")
    op.drop_table("emerging_skills")
    op.drop_table("skill_relations")
    op.drop_table("skill_implications")
    op.drop_table("skill_aliases")
    op.drop_table("skills")
