"""Add IoT telemetry events and edge sync batches.

Revision ID: 016_iot_telemetry_and_edge_sync
Revises: 015_subsea_assets_and_iot_core
Create Date: 2026-04-10
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "016_iot_telemetry_and_edge_sync"
down_revision = "015_subsea_assets_and_iot_core"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "iot_telemetry_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("organisation_id", sa.Integer(), nullable=False),
        sa.Column("device_id", sa.Integer(), nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=True),
        sa.Column("generated_alert_id", sa.Integer(), nullable=True),
        sa.Column("event_id", sa.String(length=128), nullable=True),
        sa.Column("source_type", sa.String(length=16), nullable=False),
        sa.Column("source_id", sa.String(length=128), nullable=False),
        sa.Column("telemetry_type", sa.String(length=32), nullable=False),
        sa.Column("reading_type", sa.String(length=64), nullable=True),
        sa.Column("dedupe_key", sa.String(length=64), nullable=False),
        sa.Column("correlation_mmsi", sa.String(length=32), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("normalized_json", sa.JSON(), nullable=False),
        sa.Column("severity_hint", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["device_id"], ["iot_devices.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["generated_alert_id"], ["alerts.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dedupe_key"),
    )
    op.create_index("ix_iot_telemetry_events_organisation_id", "iot_telemetry_events", ["organisation_id"])
    op.create_index("ix_iot_telemetry_events_device_id", "iot_telemetry_events", ["device_id"])
    op.create_index("ix_iot_telemetry_events_asset_id", "iot_telemetry_events", ["asset_id"])
    op.create_index("ix_iot_telemetry_events_generated_alert_id", "iot_telemetry_events", ["generated_alert_id"])
    op.create_index("ix_iot_telemetry_events_event_id", "iot_telemetry_events", ["event_id"])
    op.create_index("ix_iot_telemetry_events_source_type", "iot_telemetry_events", ["source_type"])
    op.create_index("ix_iot_telemetry_events_telemetry_type", "iot_telemetry_events", ["telemetry_type"])
    op.create_index("ix_iot_telemetry_events_reading_type", "iot_telemetry_events", ["reading_type"])
    op.create_index("ix_iot_telemetry_events_dedupe_key", "iot_telemetry_events", ["dedupe_key"])
    op.create_index("ix_iot_telemetry_events_correlation_mmsi", "iot_telemetry_events", ["correlation_mmsi"])
    op.create_index("ix_iot_telemetry_events_recorded_at", "iot_telemetry_events", ["recorded_at"])
    op.create_index("idx_iot_telemetry_org_asset_time", "iot_telemetry_events", ["organisation_id", "asset_id", "recorded_at"])
    op.create_index("idx_iot_telemetry_org_type_time", "iot_telemetry_events", ["organisation_id", "telemetry_type", "recorded_at"])

    op.create_table(
        "iot_edge_sync_batches",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("organisation_id", sa.Integer(), nullable=False),
        sa.Column("device_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("signature", sa.String(length=255), nullable=True),
        sa.Column("event_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("replayed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["device_id"], ["iot_devices.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_iot_edge_sync_batches_organisation_id", "iot_edge_sync_batches", ["organisation_id"])
    op.create_index("ix_iot_edge_sync_batches_device_id", "iot_edge_sync_batches", ["device_id"])
    op.create_index("ix_iot_edge_sync_batches_status", "iot_edge_sync_batches", ["status"])
    op.create_index("ix_iot_edge_sync_batches_uploaded_at", "iot_edge_sync_batches", ["uploaded_at"])
    op.create_index("idx_iot_edge_batches_org_device_uploaded", "iot_edge_sync_batches", ["organisation_id", "device_id", "uploaded_at"])


def downgrade() -> None:
    op.drop_index("idx_iot_edge_batches_org_device_uploaded", table_name="iot_edge_sync_batches")
    op.drop_index("ix_iot_edge_sync_batches_uploaded_at", table_name="iot_edge_sync_batches")
    op.drop_index("ix_iot_edge_sync_batches_status", table_name="iot_edge_sync_batches")
    op.drop_index("ix_iot_edge_sync_batches_device_id", table_name="iot_edge_sync_batches")
    op.drop_index("ix_iot_edge_sync_batches_organisation_id", table_name="iot_edge_sync_batches")
    op.drop_table("iot_edge_sync_batches")

    op.drop_index("idx_iot_telemetry_org_type_time", table_name="iot_telemetry_events")
    op.drop_index("idx_iot_telemetry_org_asset_time", table_name="iot_telemetry_events")
    op.drop_index("ix_iot_telemetry_events_recorded_at", table_name="iot_telemetry_events")
    op.drop_index("ix_iot_telemetry_events_correlation_mmsi", table_name="iot_telemetry_events")
    op.drop_index("ix_iot_telemetry_events_dedupe_key", table_name="iot_telemetry_events")
    op.drop_index("ix_iot_telemetry_events_reading_type", table_name="iot_telemetry_events")
    op.drop_index("ix_iot_telemetry_events_telemetry_type", table_name="iot_telemetry_events")
    op.drop_index("ix_iot_telemetry_events_source_type", table_name="iot_telemetry_events")
    op.drop_index("ix_iot_telemetry_events_event_id", table_name="iot_telemetry_events")
    op.drop_index("ix_iot_telemetry_events_generated_alert_id", table_name="iot_telemetry_events")
    op.drop_index("ix_iot_telemetry_events_asset_id", table_name="iot_telemetry_events")
    op.drop_index("ix_iot_telemetry_events_device_id", table_name="iot_telemetry_events")
    op.drop_index("ix_iot_telemetry_events_organisation_id", table_name="iot_telemetry_events")
    op.drop_table("iot_telemetry_events")