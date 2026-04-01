"""BL-009: Add evidence_hash column to alerts table.

Stores a stable SHA-256 fingerprint of the slim evidence payload so analysts
can verify evidence integrity and correlate equivalent detections.

Revision ID: 012_alert_evidence_hash
Revises:     011_alert_idempotency_key
Create Date: 2026-04-01
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "012_alert_evidence_hash"
down_revision = "011_alert_idempotency_key"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    if is_sqlite:
        with op.batch_alter_table("alerts") as batch_op:
            batch_op.add_column(
                sa.Column("evidence_hash", sa.String(64), nullable=True)
            )
            batch_op.create_index(
                "ix_alerts_evidence_hash", ["evidence_hash"], unique=False
            )
    else:
        op.add_column(
            "alerts",
            sa.Column("evidence_hash", sa.String(64), nullable=True),
        )
        op.create_index(
            "ix_alerts_evidence_hash", "alerts", ["evidence_hash"], unique=False
        )


def downgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    if is_sqlite:
        with op.batch_alter_table("alerts") as batch_op:
            batch_op.drop_index("ix_alerts_evidence_hash")
            batch_op.drop_column("evidence_hash")
    else:
        op.drop_index("ix_alerts_evidence_hash", table_name="alerts")
        op.drop_column("alerts", "evidence_hash")
