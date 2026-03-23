"""organisations table and organisation_id on tenant tables

Revision ID: 008_organisations
Revises: 007_merge_006_heads
Create Date: 2026-03-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "008_organisations"
down_revision: Union[str, None] = "007_merge_006_heads"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    op.create_table(
        "organisations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("settings", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_organisations_slug", "organisations", ["slug"], unique=True)

    op.execute(
        sa.text(
            "INSERT INTO organisations (id, name, slug) VALUES (1, 'Default', 'default')"
        )
    )
    if bind.dialect.name == "postgresql":
        op.execute(
            sa.text(
                "SELECT setval(pg_get_serial_sequence('organisations', 'id'), "
                "(SELECT MAX(id) FROM organisations))"
            )
        )

    op.add_column("users", sa.Column("organisation_id", sa.Integer(), nullable=True))
    op.add_column("alerts", sa.Column("organisation_id", sa.Integer(), nullable=True))
    op.add_column("watchlist_entries", sa.Column("organisation_id", sa.Integer(), nullable=True))
    op.add_column("audit_logs", sa.Column("organisation_id", sa.Integer(), nullable=True))
    op.add_column(
        "itdae_geofence_zones",
        sa.Column("organisation_id", sa.Integer(), nullable=True),
    )

    op.execute(sa.text("UPDATE users SET organisation_id = 1 WHERE organisation_id IS NULL"))
    op.execute(sa.text("UPDATE alerts SET organisation_id = 1 WHERE organisation_id IS NULL"))
    op.execute(
        sa.text(
            "UPDATE watchlist_entries SET organisation_id = 1 WHERE organisation_id IS NULL"
        )
    )
    op.execute(sa.text("UPDATE audit_logs SET organisation_id = 1 WHERE organisation_id IS NULL"))
    op.execute(
        sa.text(
            "UPDATE itdae_geofence_zones SET organisation_id = 1 WHERE organisation_id IS NULL"
        )
    )

    if is_sqlite:
        with op.batch_alter_table("watchlist_entries") as batch_op:
            batch_op.drop_constraint("uq_watchlist_entries_mmsi", type_="unique")
    else:
        op.drop_constraint("uq_watchlist_entries_mmsi", "watchlist_entries", type_="unique")

    # SQLite requires batch mode for NOT NULL alters; PostgreSQL can use plain ALTER.
    if is_sqlite:
        with op.batch_alter_table("users") as batch_op:
            batch_op.alter_column("organisation_id", existing_type=sa.Integer(), nullable=False)
        with op.batch_alter_table("alerts") as batch_op:
            batch_op.alter_column("organisation_id", existing_type=sa.Integer(), nullable=False)
        with op.batch_alter_table("watchlist_entries") as batch_op:
            batch_op.alter_column("organisation_id", existing_type=sa.Integer(), nullable=False)
        with op.batch_alter_table("audit_logs") as batch_op:
            batch_op.alter_column("organisation_id", existing_type=sa.Integer(), nullable=False)
        with op.batch_alter_table("itdae_geofence_zones") as batch_op:
            batch_op.alter_column("organisation_id", existing_type=sa.Integer(), nullable=False)
    else:
        op.alter_column("users", "organisation_id", existing_type=sa.Integer(), nullable=False)
        op.alter_column("alerts", "organisation_id", existing_type=sa.Integer(), nullable=False)
        op.alter_column(
            "watchlist_entries", "organisation_id", existing_type=sa.Integer(), nullable=False
        )
        op.alter_column("audit_logs", "organisation_id", existing_type=sa.Integer(), nullable=False)
        op.alter_column(
            "itdae_geofence_zones",
            "organisation_id",
            existing_type=sa.Integer(),
            nullable=False,
        )

    # SQLite cannot ALTER ADD CONSTRAINT; skip FK DDL on SQLite (dev-only default DB).
    if not is_sqlite:
        op.create_foreign_key(
            "fk_users_organisation_id",
            "users",
            "organisations",
            ["organisation_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        op.create_foreign_key(
            "fk_alerts_organisation_id",
            "alerts",
            "organisations",
            ["organisation_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        op.create_foreign_key(
            "fk_watchlist_entries_organisation_id",
            "watchlist_entries",
            "organisations",
            ["organisation_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        op.create_foreign_key(
            "fk_audit_logs_organisation_id",
            "audit_logs",
            "organisations",
            ["organisation_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        op.create_foreign_key(
            "fk_itdae_geofence_zones_organisation_id",
            "itdae_geofence_zones",
            "organisations",
            ["organisation_id"],
            ["id"],
            ondelete="RESTRICT",
        )

    op.create_index("ix_users_organisation_id", "users", ["organisation_id"], unique=False)
    op.create_index("ix_alerts_organisation_id", "alerts", ["organisation_id"], unique=False)
    op.create_index(
        "ix_watchlist_entries_organisation_id",
        "watchlist_entries",
        ["organisation_id"],
        unique=False,
    )
    op.create_index(
        "ix_audit_logs_organisation_id", "audit_logs", ["organisation_id"], unique=False
    )
    op.create_index(
        "ix_itdae_geofence_zones_organisation_id",
        "itdae_geofence_zones",
        ["organisation_id"],
        unique=False,
    )

    if is_sqlite:
        with op.batch_alter_table("watchlist_entries") as batch_op:
            batch_op.create_unique_constraint(
                "uq_watchlist_entries_org_mmsi",
                ["organisation_id", "mmsi"],
            )
    else:
        op.create_unique_constraint(
            "uq_watchlist_entries_org_mmsi",
            "watchlist_entries",
            ["organisation_id", "mmsi"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"

    if is_sqlite:
        with op.batch_alter_table("watchlist_entries") as batch_op:
            batch_op.drop_constraint("uq_watchlist_entries_org_mmsi", type_="unique")
    else:
        op.drop_constraint(
            "uq_watchlist_entries_org_mmsi", "watchlist_entries", type_="unique"
        )

    if is_sqlite:
        with op.batch_alter_table("watchlist_entries") as batch_op:
            batch_op.create_unique_constraint("uq_watchlist_entries_mmsi", ["mmsi"])
    else:
        op.create_unique_constraint(
            "uq_watchlist_entries_mmsi", "watchlist_entries", ["mmsi"]
        )

    op.drop_index("ix_itdae_geofence_zones_organisation_id", table_name="itdae_geofence_zones")
    op.drop_index("ix_audit_logs_organisation_id", table_name="audit_logs")
    op.drop_index("ix_watchlist_entries_organisation_id", table_name="watchlist_entries")
    op.drop_index("ix_alerts_organisation_id", table_name="alerts")
    op.drop_index("ix_users_organisation_id", table_name="users")

    if not is_sqlite:
        op.drop_constraint("fk_itdae_geofence_zones_organisation_id", "itdae_geofence_zones", type_="foreignkey")
        op.drop_constraint("fk_audit_logs_organisation_id", "audit_logs", type_="foreignkey")
        op.drop_constraint("fk_watchlist_entries_organisation_id", "watchlist_entries", type_="foreignkey")
        op.drop_constraint("fk_alerts_organisation_id", "alerts", type_="foreignkey")
        op.drop_constraint("fk_users_organisation_id", "users", type_="foreignkey")

    op.drop_column("itdae_geofence_zones", "organisation_id")
    op.drop_column("audit_logs", "organisation_id")
    op.drop_column("watchlist_entries", "organisation_id")
    op.drop_column("alerts", "organisation_id")
    op.drop_column("users", "organisation_id")

    op.drop_index("ix_organisations_slug", table_name="organisations")
    op.drop_table("organisations")
