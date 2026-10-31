"""Add matches.blind column for blind screening (Feature F4, Step 4.8).

Revision ID: 0003_add_matches_blind
Revises: 0002_portfolio_rescope
Create Date: 2026-10-31
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_add_matches_blind"
down_revision: str | None = "0002_portfolio_rescope"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "matches",
        sa.Column("blind", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("matches", "blind")
