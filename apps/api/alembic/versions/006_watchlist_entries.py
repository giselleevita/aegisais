"""watchlist_entries table

Revision ID: 006_watchlist
Revises: 005_audit_logs
Create Date: 2026-03-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "006_watchlist"
down_revision: Union[str, None] = "005_audit_logs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "watchlist_entries",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("mmsi", sa.String(), nullable=False),
        sa.Column("label", sa.String(), nullable=False),
        sa.Column("priority", sa.String(), nullable=False),
        sa.Column("added_by_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["added_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("mmsi", name="uq_watchlist_entries_mmsi"),
    )
    op.create_index("ix_watchlist_entries_mmsi", "watchlist_entries", ["mmsi"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_watchlist_entries_mmsi", table_name="watchlist_entries")
    op.drop_table("watchlist_entries")
