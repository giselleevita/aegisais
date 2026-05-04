"""Add organisation_id to vessels_latest and vessel_positions for per-tenant scoping.

Revision ID: 015_vessel_org_scoping
Revises: 014_add_user_mfa_columns
Create Date: 2026-03-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "015_vessel_org_scoping"
down_revision: Union[str, None] = "014_add_user_mfa_columns"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"
    inspector = sa.inspect(bind)

    # ── vessels_latest ─────────────────────────────────────────────────────────
    vessels_latest_columns = [col["name"] for col in inspector.get_columns("vessels_latest")]
    if "organisation_id" not in vessels_latest_columns:
        op.add_column(
            "vessels_latest",
            sa.Column("organisation_id", sa.Integer(), nullable=True),
        )
        # Backfill existing rows to the default organisation (id=1)
        op.execute(sa.text("UPDATE vessels_latest SET organisation_id = 1 WHERE organisation_id IS NULL"))

        if not is_sqlite:
            op.create_foreign_key(
                "fk_vessels_latest_org",
                "vessels_latest",
                "organisations",
                ["organisation_id"],
                ["id"],
                ondelete="SET NULL",
            )
        op.create_index("ix_vessels_latest_org", "vessels_latest", ["organisation_id"])

    # ── vessel_positions ───────────────────────────────────────────────────────
    vessel_positions_columns = [col["name"] for col in inspector.get_columns("vessel_positions")]
    if "organisation_id" not in vessel_positions_columns:
        op.add_column(
            "vessel_positions",
            sa.Column("organisation_id", sa.Integer(), nullable=True),
        )
        op.execute(sa.text("UPDATE vessel_positions SET organisation_id = 1 WHERE organisation_id IS NULL"))

        if not is_sqlite:
            op.create_foreign_key(
                "fk_vessel_positions_org",
                "vessel_positions",
                "organisations",
                ["organisation_id"],
                ["id"],
                ondelete="SET NULL",
            )
        op.create_index("ix_vessel_positions_org", "vessel_positions", ["organisation_id"])


def downgrade() -> None:
    op.drop_index("ix_vessel_positions_org", table_name="vessel_positions")
    op.drop_column("vessel_positions", "organisation_id")
    op.drop_index("ix_vessels_latest_org", table_name="vessels_latest")
    op.drop_column("vessels_latest", "organisation_id")
