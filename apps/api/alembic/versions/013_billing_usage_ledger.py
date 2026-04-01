"""BL-010: Create usage_ledger table for append-only billable event records.

Revision ID: 013_billing_usage_ledger
Revises:     012_alert_evidence_hash
Create Date: 2026-04-01
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "013_billing_usage_ledger"
down_revision = "012_alert_evidence_hash"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "usage_ledger",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("organisation_id", sa.Integer(), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
        ),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column(
            "quantity",
            sa.Numeric(precision=18, scale=6),
            nullable=False,
            default=1,
        ),
        sa.Column("reference_id", sa.Integer(), nullable=True),
        sa.Column("reference_key", sa.String(255), nullable=True),
        sa.ForeignKeyConstraint(
            ["organisation_id"],
            ["organisations.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_usage_ledger_org_id",
        "usage_ledger",
        ["organisation_id"],
        unique=False,
    )
    op.create_index(
        "ix_usage_ledger_occurred_at",
        "usage_ledger",
        ["occurred_at"],
        unique=False,
    )
    op.create_index(
        "ix_usage_ledger_event_type",
        "usage_ledger",
        ["event_type"],
        unique=False,
    )
    op.create_index(
        "ix_usage_ledger_org_type_occurred",
        "usage_ledger",
        ["organisation_id", "event_type", "occurred_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_usage_ledger_org_type_occurred", table_name="usage_ledger")
    op.drop_index("ix_usage_ledger_event_type", table_name="usage_ledger")
    op.drop_index("ix_usage_ledger_occurred_at", table_name="usage_ledger")
    op.drop_index("ix_usage_ledger_org_id", table_name="usage_ledger")
    op.drop_table("usage_ledger")
