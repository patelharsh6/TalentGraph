"""Portfolio re-scope (ADR-0003): drop webhooks, API-key ownership and the emerging-skill review.

- `webhook_deliveries` and `batch_jobs.callback_url` go (no webhooks).
- `api_keys` and every `api_key_id` column go (one API key from the environment, no ownership).
- `emerging_skills` keeps only the unrecognized-skill store (no review workflow).

Downgrade restores the columns and tables, but `api_key_id` comes back nullable because the
dropped values cannot be recovered.

Revision ID: 0002_portfolio_rescope
Revises: 0001_initial_schema
Create Date: 2026-10-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_portfolio_rescope"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_OWNED_TABLES = ("candidates", "jobs", "batch_jobs")


def upgrade() -> None:
    op.drop_table("webhook_deliveries")
    op.drop_column("batch_jobs", "callback_url")
    for table in _OWNED_TABLES:
        op.drop_column(table, "api_key_id")  # also drops its index and foreign key
    op.drop_table("api_keys")
    for column in ("status", "merged_into", "reviewed_by", "reviewed_at"):
        op.drop_column("emerging_skills", column)


def downgrade() -> None:
    op.add_column(
        "emerging_skills",
        sa.Column(
            "status", sa.String(length=20), server_default=sa.text("'pending'"), nullable=False
        ),
    )
    op.add_column(
        "emerging_skills",
        sa.Column("merged_into", sa.Integer(), sa.ForeignKey("skills.id"), nullable=True),
    )
    op.add_column("emerging_skills", sa.Column("reviewed_by", sa.String(length=100), nullable=True))
    op.add_column(
        "emerging_skills", sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True)
    )

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
    for table in _OWNED_TABLES:
        op.add_column(
            table,
            sa.Column("api_key_id", sa.Integer(), sa.ForeignKey("api_keys.id"), nullable=True),
        )
        op.create_index(f"ix_{table}_api_key_id", table, ["api_key_id"], unique=False)

    op.add_column("batch_jobs", sa.Column("callback_url", sa.String(length=2000), nullable=True))
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
