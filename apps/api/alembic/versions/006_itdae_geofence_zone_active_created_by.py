"""itdae_geofence_zones: is_active, created_by_id

Revision ID: 006_itdae_geofence_meta
Revises: 005_audit_logs
Create Date: 2026-03-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "006_itdae_geofence_meta"
down_revision: Union[str, None] = "005_audit_logs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    if is_sqlite:
        with op.batch_alter_table("itdae_geofence_zones") as batch_op:
            batch_op.add_column(
                sa.Column("is_active", sa.Boolean(), server_default=sa.text("1"), nullable=False)
            )
            batch_op.add_column(sa.Column("created_by_id", sa.Integer(), nullable=True))
    else:
        op.add_column(
            "itdae_geofence_zones",
            sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        )
        op.add_column(
            "itdae_geofence_zones",
            sa.Column("created_by_id", sa.Integer(), nullable=True),
        )
        op.create_foreign_key(
            "fk_itdae_geofence_zones_created_by",
            "itdae_geofence_zones",
            "users",
            ["created_by_id"],
            ["id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    if is_sqlite:
        with op.batch_alter_table("itdae_geofence_zones") as batch_op:
            batch_op.drop_column("created_by_id")
            batch_op.drop_column("is_active")
    else:
        op.drop_constraint("fk_itdae_geofence_zones_created_by", "itdae_geofence_zones", type_="foreignkey")
        op.drop_column("itdae_geofence_zones", "created_by_id")
        op.drop_column("itdae_geofence_zones", "is_active")
