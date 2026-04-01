"""add organisation_id to vessel tables for tenant scoping

Revision ID: 010_vessel_org_scope
Revises: 009_merge_008_pw_incidents
Create Date: 2026-03-30

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "010_vessel_org_scope"
down_revision: Union[str, None] = "009_merge_008_pw_incidents"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    if is_sqlite:
        with op.batch_alter_table("vessels_latest") as batch_op:
            batch_op.add_column(sa.Column("organisation_id", sa.Integer(), nullable=False, server_default="1"))
            batch_op.create_index("ix_vessels_latest_organisation_id", ["organisation_id"], unique=False)
            batch_op.create_foreign_key(
                "fk_vessels_latest_org",
                "organisations",
                ["organisation_id"],
                ["id"],
                ondelete="RESTRICT",
            )

        with op.batch_alter_table("vessel_positions") as batch_op:
            batch_op.add_column(sa.Column("organisation_id", sa.Integer(), nullable=False, server_default="1"))
            batch_op.create_index("ix_vessel_positions_organisation_id", ["organisation_id"], unique=False)
            batch_op.create_foreign_key(
                "fk_vessel_positions_org",
                "organisations",
                ["organisation_id"],
                ["id"],
                ondelete="RESTRICT",
            )
    else:
        op.add_column(
            "vessels_latest",
            sa.Column("organisation_id", sa.Integer(), nullable=False, server_default="1"),
        )
        op.create_index("ix_vessels_latest_organisation_id", "vessels_latest", ["organisation_id"], unique=False)
        op.create_foreign_key(
            "fk_vessels_latest_org",
            "vessels_latest",
            "organisations",
            ["organisation_id"],
            ["id"],
            ondelete="RESTRICT",
        )

        op.add_column(
            "vessel_positions",
            sa.Column("organisation_id", sa.Integer(), nullable=False, server_default="1"),
        )
        op.create_index("ix_vessel_positions_organisation_id", "vessel_positions", ["organisation_id"], unique=False)
        op.create_foreign_key(
            "fk_vessel_positions_org",
            "vessel_positions",
            "organisations",
            ["organisation_id"],
            ["id"],
            ondelete="RESTRICT",
        )

    op.create_index(
        "idx_vessels_org_mmsi",
        "vessels_latest",
        ["organisation_id", "mmsi"],
        unique=False,
    )
    op.create_index(
        "idx_vessel_positions_org_mmsi_time",
        "vessel_positions",
        ["organisation_id", "mmsi", "timestamp"],
        unique=False,
    )


def downgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    op.drop_index("idx_vessel_positions_org_mmsi_time", table_name="vessel_positions")
    op.drop_index("idx_vessels_org_mmsi", table_name="vessels_latest")

    if is_sqlite:
        with op.batch_alter_table("vessel_positions") as batch_op:
            batch_op.drop_constraint("fk_vessel_positions_org", type_="foreignkey")
            batch_op.drop_index("ix_vessel_positions_organisation_id")
            batch_op.drop_column("organisation_id")

        with op.batch_alter_table("vessels_latest") as batch_op:
            batch_op.drop_constraint("fk_vessels_latest_org", type_="foreignkey")
            batch_op.drop_index("ix_vessels_latest_organisation_id")
            batch_op.drop_column("organisation_id")
    else:
        op.drop_constraint("fk_vessel_positions_org", "vessel_positions", type_="foreignkey")
        op.drop_index("ix_vessel_positions_organisation_id", table_name="vessel_positions")
        op.drop_column("vessel_positions", "organisation_id")

        op.drop_constraint("fk_vessels_latest_org", "vessels_latest", type_="foreignkey")
        op.drop_index("ix_vessels_latest_organisation_id", table_name="vessels_latest")
        op.drop_column("vessels_latest", "organisation_id")
