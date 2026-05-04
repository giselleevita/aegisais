"""Add subsea asset and IoT core tables.

Revision ID: 015_subsea_assets_and_iot_core
Revises: 014_add_user_mfa_columns
Create Date: 2026-04-10
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "015_subsea_assets_and_iot_core"
down_revision = "014_add_user_mfa_columns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "assets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("organisation_id", sa.Integer(), nullable=False),
        sa.Column("asset_type", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("criticality", sa.String(length=16), nullable=False),
        sa.Column("geometry_json", sa.JSON(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_assets_asset_type", "assets", ["asset_type"])
    op.create_index("ix_assets_criticality", "assets", ["criticality"])
    op.create_index("ix_assets_is_active", "assets", ["is_active"])
    op.create_index("ix_assets_organisation_id", "assets", ["organisation_id"])
    op.create_index("ix_assets_status", "assets", ["status"])
    op.create_index("idx_assets_org_type_active", "assets", ["organisation_id", "asset_type", "is_active"])
    op.create_index("idx_assets_org_criticality", "assets", ["organisation_id", "criticality"])

    op.create_table(
        "asset_links",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("organisation_id", sa.Integer(), nullable=False),
        sa.Column("source_asset_id", sa.Integer(), nullable=False),
        sa.Column("target_asset_id", sa.Integer(), nullable=False),
        sa.Column("relation_type", sa.String(length=32), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["source_asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_asset_id", "target_asset_id", "relation_type", name="uq_asset_links_directional_relation"),
    )
    op.create_index("ix_asset_links_organisation_id", "asset_links", ["organisation_id"])
    op.create_index("ix_asset_links_relation_type", "asset_links", ["relation_type"])
    op.create_index("ix_asset_links_source_asset_id", "asset_links", ["source_asset_id"])
    op.create_index("ix_asset_links_target_asset_id", "asset_links", ["target_asset_id"])
    op.create_index("idx_asset_links_org_source", "asset_links", ["organisation_id", "source_asset_id"])
    op.create_index("idx_asset_links_org_target", "asset_links", ["organisation_id", "target_asset_id"])

    op.create_table(
        "asset_policies",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("organisation_id", sa.Integer(), nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("policy_type", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("policy_json", sa.JSON(), nullable=False),
        sa.Column("active_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("active_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_asset_policies_active_from", "asset_policies", ["active_from"])
    op.create_index("ix_asset_policies_active_to", "asset_policies", ["active_to"])
    op.create_index("ix_asset_policies_asset_id", "asset_policies", ["asset_id"])
    op.create_index("ix_asset_policies_is_active", "asset_policies", ["is_active"])
    op.create_index("ix_asset_policies_organisation_id", "asset_policies", ["organisation_id"])
    op.create_index("ix_asset_policies_policy_type", "asset_policies", ["policy_type"])
    op.create_index("idx_asset_policies_org_asset_type", "asset_policies", ["organisation_id", "asset_id", "policy_type"])

    op.create_table(
        "iot_devices",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("organisation_id", sa.Integer(), nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=True),
        sa.Column("device_type", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("firmware_version", sa.String(length=64), nullable=True),
        sa.Column("certificate_ref", sa.String(length=255), nullable=True),
        sa.Column("connectivity_profile", sa.JSON(), nullable=True),
        sa.Column("location_json", sa.JSON(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_iot_devices_asset_id", "iot_devices", ["asset_id"])
    op.create_index("ix_iot_devices_device_type", "iot_devices", ["device_type"])
    op.create_index("ix_iot_devices_is_active", "iot_devices", ["is_active"])
    op.create_index("ix_iot_devices_last_seen_at", "iot_devices", ["last_seen_at"])
    op.create_index("ix_iot_devices_organisation_id", "iot_devices", ["organisation_id"])
    op.create_index("ix_iot_devices_status", "iot_devices", ["status"])
    op.create_index("idx_iot_devices_org_type_status", "iot_devices", ["organisation_id", "device_type", "status"])
    op.create_index("idx_iot_devices_org_asset", "iot_devices", ["organisation_id", "asset_id"])

    op.create_table(
        "iot_device_heartbeats",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("organisation_id", sa.Integer(), nullable=False),
        sa.Column("device_id", sa.Integer(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("battery_level", sa.Float(), nullable=True),
        sa.Column("queue_depth", sa.Integer(), nullable=True),
        sa.Column("signal_strength", sa.Float(), nullable=True),
        sa.Column("details_json", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["device_id"], ["iot_devices.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organisation_id"], ["organisations.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_iot_device_heartbeats_device_id", "iot_device_heartbeats", ["device_id"])
    op.create_index("ix_iot_device_heartbeats_organisation_id", "iot_device_heartbeats", ["organisation_id"])
    op.create_index("ix_iot_device_heartbeats_recorded_at", "iot_device_heartbeats", ["recorded_at"])
    op.create_index("ix_iot_device_heartbeats_status", "iot_device_heartbeats", ["status"])
    op.create_index("idx_iot_heartbeats_org_device_time", "iot_device_heartbeats", ["organisation_id", "device_id", "recorded_at"])

    op.add_column("alerts", sa.Column("asset_id", sa.Integer(), nullable=True))
    op.add_column("alerts", sa.Column("source_device_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_alerts_asset_id", "alerts", "assets", ["asset_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_alerts_source_device_id", "alerts", "iot_devices", ["source_device_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_alerts_asset_id", "alerts", ["asset_id"])
    op.create_index("ix_alerts_source_device_id", "alerts", ["source_device_id"])
    op.create_index("idx_alerts_org_asset_time", "alerts", ["organisation_id", "asset_id", "timestamp"])

    op.add_column("incidents", sa.Column("asset_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_incidents_asset_id", "incidents", "assets", ["asset_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_incidents_asset_id", "incidents", ["asset_id"])
    op.create_index("idx_incidents_org_asset", "incidents", ["organisation_id", "asset_id"])


def downgrade() -> None:
    op.drop_index("idx_incidents_org_asset", table_name="incidents")
    op.drop_index("ix_incidents_asset_id", table_name="incidents")
    op.drop_constraint("fk_incidents_asset_id", "incidents", type_="foreignkey")
    op.drop_column("incidents", "asset_id")

    op.drop_index("idx_alerts_org_asset_time", table_name="alerts")
    op.drop_index("ix_alerts_source_device_id", table_name="alerts")
    op.drop_index("ix_alerts_asset_id", table_name="alerts")
    op.drop_constraint("fk_alerts_source_device_id", "alerts", type_="foreignkey")
    op.drop_constraint("fk_alerts_asset_id", "alerts", type_="foreignkey")
    op.drop_column("alerts", "source_device_id")
    op.drop_column("alerts", "asset_id")

    op.drop_index("idx_iot_heartbeats_org_device_time", table_name="iot_device_heartbeats")
    op.drop_index("ix_iot_device_heartbeats_status", table_name="iot_device_heartbeats")
    op.drop_index("ix_iot_device_heartbeats_recorded_at", table_name="iot_device_heartbeats")
    op.drop_index("ix_iot_device_heartbeats_organisation_id", table_name="iot_device_heartbeats")
    op.drop_index("ix_iot_device_heartbeats_device_id", table_name="iot_device_heartbeats")
    op.drop_table("iot_device_heartbeats")

    op.drop_index("idx_iot_devices_org_asset", table_name="iot_devices")
    op.drop_index("idx_iot_devices_org_type_status", table_name="iot_devices")
    op.drop_index("ix_iot_devices_status", table_name="iot_devices")
    op.drop_index("ix_iot_devices_organisation_id", table_name="iot_devices")
    op.drop_index("ix_iot_devices_last_seen_at", table_name="iot_devices")
    op.drop_index("ix_iot_devices_is_active", table_name="iot_devices")
    op.drop_index("ix_iot_devices_device_type", table_name="iot_devices")
    op.drop_index("ix_iot_devices_asset_id", table_name="iot_devices")
    op.drop_table("iot_devices")

    op.drop_index("idx_asset_policies_org_asset_type", table_name="asset_policies")
    op.drop_index("ix_asset_policies_policy_type", table_name="asset_policies")
    op.drop_index("ix_asset_policies_organisation_id", table_name="asset_policies")
    op.drop_index("ix_asset_policies_is_active", table_name="asset_policies")
    op.drop_index("ix_asset_policies_asset_id", table_name="asset_policies")
    op.drop_index("ix_asset_policies_active_to", table_name="asset_policies")
    op.drop_index("ix_asset_policies_active_from", table_name="asset_policies")
    op.drop_table("asset_policies")

    op.drop_index("idx_asset_links_org_target", table_name="asset_links")
    op.drop_index("idx_asset_links_org_source", table_name="asset_links")
    op.drop_index("ix_asset_links_target_asset_id", table_name="asset_links")
    op.drop_index("ix_asset_links_source_asset_id", table_name="asset_links")
    op.drop_index("ix_asset_links_relation_type", table_name="asset_links")
    op.drop_index("ix_asset_links_organisation_id", table_name="asset_links")
    op.drop_table("asset_links")

    op.drop_index("idx_assets_org_criticality", table_name="assets")
    op.drop_index("idx_assets_org_type_active", table_name="assets")
    op.drop_index("ix_assets_status", table_name="assets")
    op.drop_index("ix_assets_organisation_id", table_name="assets")
    op.drop_index("ix_assets_is_active", table_name="assets")
    op.drop_index("ix_assets_criticality", table_name="assets")
    op.drop_index("ix_assets_asset_type", table_name="assets")
    op.drop_table("assets")
