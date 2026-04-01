"""add idempotency_key to alerts table (BL-003)

Revision ID: 011_alert_idempotency_key
Revises: 010_vessel_org_scope
Create Date: 2026-03-31

Idempotency contract (BL-003)
------------------------------
The ``idempotency_key`` column provides **constraint-backed** deduplication for
the alert persistence worker.

Key derivation
    sha256( "{org_id}:{mmsi}:{alert_type}:{minute_bucket_utc}" )

    The minute-level UTC bucket absorbs sub-second drift and different
    ISO-8601 serialisation formats while still giving per-rule, per-vessel,
    per-minute uniqueness.  See ``derive_alert_idempotency_key`` in
    ``app.modules.alerts.models``.

Why NULLABLE
    Existing rows created before this migration have no key.  The application
    fills the column on every new INSERT; legacy rows are left NULL (NULL is
    excluded from the unique constraint on both PostgreSQL and SQLite, so
    multiple legacy NULLs are permitted).

Worker behaviour
    The worker computes the key before INSERT, then uses a savepoint to catch
    ``IntegrityError`` and short-circuit to the already-committed row, making
    the at-least-once Redis-stream delivery fully idempotent.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "011_alert_idempotency_key"
down_revision: Union[str, None] = "010_vessel_org_scope"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    if is_sqlite:
        with op.batch_alter_table("alerts") as batch_op:
            batch_op.add_column(
                sa.Column("idempotency_key", sa.String(), nullable=True)
            )
            batch_op.create_index(
                "ix_alerts_idempotency_key", ["idempotency_key"], unique=True
            )
    else:
        op.add_column(
            "alerts",
            sa.Column("idempotency_key", sa.String(), nullable=True),
        )
        op.create_index(
            "ix_alerts_idempotency_key", "alerts", ["idempotency_key"], unique=True
        )


def downgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    if is_sqlite:
        with op.batch_alter_table("alerts") as batch_op:
            batch_op.drop_index("ix_alerts_idempotency_key")
            batch_op.drop_column("idempotency_key")
    else:
        op.drop_index("ix_alerts_idempotency_key", table_name="alerts")
        op.drop_column("alerts", "idempotency_key")
