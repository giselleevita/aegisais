"""add_incidents_table

Revision ID: e7a1c9d2f301
Revises: 008_organisations
Create Date: 2026-03-23 12:00:00.000000

Concurrency and uniqueness notes
---------------------------------
The ``incidents`` table enforces a **database-level** unique constraint on
``alert_id`` (``uq_incidents_alert_id`` / ``ix_incidents_alert_id``).

This is the last-resort guard against duplicate incident rows under concurrent
worker execution.  The application layer (``create_incident_from_alert_with_flag``)
also uses a savepoint-based optimistic check to avoid relying solely on the
database constraint, but the constraint must exist independently so that:

1. Direct database inserts (e.g. data migrations, manual tooling) are also
   protected.
2. Any future worker path that bypasses the service layer cannot silently
   create duplicates.
3. The constraint is provably present in production and therefore safe to
   assert in CI regression tests.

If two workers race to create an incident for the same alert, exactly one
INSERT will succeed; the loser receives an ``IntegrityError`` which the
service layer recovers from by re-querying for the already-committed row.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "e7a1c9d2f301"
down_revision: Union[str, None] = "008_organisations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "incidents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organisation_id", sa.Integer(), nullable=False),
        sa.Column("alert_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("evidence_bundle", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["alert_id"], ["alerts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["organisation_id"], ["organisations.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("alert_id"),
    )
    op.create_index(op.f("ix_incidents_alert_id"), "incidents", ["alert_id"], unique=True)
    op.create_index(
        op.f("ix_incidents_created_at"), "incidents", ["created_at"], unique=False
    )
    op.create_index(
        op.f("ix_incidents_organisation_id"),
        "incidents",
        ["organisation_id"],
        unique=False,
    )
    op.create_index(op.f("ix_incidents_status"), "incidents", ["status"], unique=False)
    op.create_index(
        "idx_incidents_org_created",
        "incidents",
        ["organisation_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_incidents_org_created", table_name="incidents")
    op.drop_index(op.f("ix_incidents_status"), table_name="incidents")
    op.drop_index(op.f("ix_incidents_organisation_id"), table_name="incidents")
    op.drop_index(op.f("ix_incidents_created_at"), table_name="incidents")
    op.drop_index(op.f("ix_incidents_alert_id"), table_name="incidents")
    op.drop_table("incidents")
