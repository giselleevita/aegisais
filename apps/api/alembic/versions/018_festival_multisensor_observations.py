"""Festival multi-sensor observations, fusion events and evidence metadata.

Revision ID: 018_festival_multisensor
Revises: 016_iot_telemetry_and_edge_sync, 017_merge_iot_vessel_org_heads
Create Date: 2026-07-17
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "018_festival_multisensor"
down_revision: Union[str, Sequence[str], None] = (
    "016_iot_telemetry_and_edge_sync",
    "017_merge_iot_vessel_org_heads",
)
branch_labels = None
depends_on = None


def _columns(table: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()

    op.create_table(
        "observations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("organisation_id", sa.Integer(), sa.ForeignKey("organisations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("entity_id", sa.String(), nullable=False),
        sa.Column("layer_id", sa.String(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("geometry", sa.JSON(), nullable=False),
        sa.Column("properties", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.JSON(), nullable=False),
        sa.Column("provenance", sa.JSON(), nullable=False),
        sa.Column("access", sa.JSON(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=64), nullable=False),
        sa.UniqueConstraint("organisation_id", "idempotency_key", name="uq_observation_org_idempotency"),
    )
    op.create_index("ix_observations_organisation_id", "observations", ["organisation_id"])
    op.create_index("ix_observations_entity_id", "observations", ["entity_id"])
    op.create_index("ix_observations_layer_id", "observations", ["layer_id"])
    op.create_index("ix_observations_observed_at", "observations", ["observed_at"])
    op.create_index("ix_observations_ingested_at", "observations", ["ingested_at"])
    op.create_index("idx_observations_org_layer_time", "observations", ["organisation_id", "layer_id", "observed_at"])
    op.create_index("idx_observations_org_entity_time", "observations", ["organisation_id", "entity_id", "observed_at"])

    if bind.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
        op.execute(
            "ALTER TABLE observations ADD COLUMN geom geometry(Point,4326) "
            "GENERATED ALWAYS AS (ST_SetSRID(ST_MakePoint(longitude, latitude),4326)) STORED"
        )
        op.execute("CREATE INDEX idx_observations_geom ON observations USING GIST (geom)")

    op.create_table(
        "fusion_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("organisation_id", sa.Integer(), sa.ForeignKey("organisations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("entity_ids", sa.JSON(), nullable=False),
        sa.Column("observation_ids", sa.JSON(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("severity", sa.String(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("attributes", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.JSON(), nullable=False),
        sa.Column("provenance", sa.JSON(), nullable=False),
        sa.Column("access", sa.JSON(), nullable=False),
    )
    op.create_index("ix_fusion_events_organisation_id", "fusion_events", ["organisation_id"])
    op.create_index("ix_fusion_events_event_type", "fusion_events", ["event_type"])
    op.create_index("ix_fusion_events_occurred_at", "fusion_events", ["occurred_at"])
    op.create_index("idx_fusion_events_org_type_time", "fusion_events", ["organisation_id", "event_type", "occurred_at"])

    alert_columns = _columns("alerts")
    if "confidence" not in alert_columns:
        op.add_column("alerts", sa.Column("confidence", sa.JSON(), nullable=True))
    if "provenance" not in alert_columns:
        op.add_column("alerts", sa.Column("provenance", sa.JSON(), nullable=True))
    if "fusion_event_id" not in alert_columns:
        op.add_column("alerts", sa.Column("fusion_event_id", sa.String(length=36), nullable=True))
        op.create_index("ix_alerts_fusion_event_id", "alerts", ["fusion_event_id"])
        if bind.dialect.name != "sqlite":
            op.create_foreign_key(
                "fk_alert_fusion_event",
                "alerts",
                "fusion_events",
                ["fusion_event_id"],
                ["id"],
                ondelete="SET NULL",
            )

    for table in ("vessels_latest", "vessel_positions"):
        columns = _columns(table)
        if "source" not in columns:
            op.add_column(table, sa.Column("source", sa.String(), nullable=False, server_default="ais"))
        if "confidence" not in columns:
            op.add_column(table, sa.Column("confidence", sa.Float(), nullable=False, server_default="0.8"))
        if "provenance" not in columns:
            op.add_column(table, sa.Column("provenance", sa.JSON(), nullable=False, server_default="{}"))
    if "updated_at" not in _columns("vessels_latest"):
        op.add_column("vessels_latest", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    for table in ("vessel_positions", "vessels_latest"):
        for column in ("provenance", "confidence", "source"):
            if column in _columns(table):
                op.drop_column(table, column)
    if "updated_at" in _columns("vessels_latest"):
        op.drop_column("vessels_latest", "updated_at")

    if "fusion_event_id" in _columns("alerts"):
        if bind.dialect.name != "sqlite":
            op.drop_constraint("fk_alert_fusion_event", "alerts", type_="foreignkey")
        op.drop_index("ix_alerts_fusion_event_id", table_name="alerts")
        op.drop_column("alerts", "fusion_event_id")
    for column in ("provenance", "confidence"):
        if column in _columns("alerts"):
            op.drop_column("alerts", column)

    op.drop_table("fusion_events")
    op.drop_table("observations")
