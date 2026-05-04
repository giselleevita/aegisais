from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.sql import func

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Device(Base):
    __tablename__ = "iot_devices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    organisation_id = Column(
        Integer,
        ForeignKey("organisations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="SET NULL"), nullable=True, index=True)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    device_type = Column(String(32), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    status = Column(String(32), nullable=False, default="active", index=True)
    firmware_version = Column(String(64), nullable=True)
    certificate_ref = Column(String(255), nullable=True)
    connectivity_profile = Column(JSON, nullable=True)
    location_json = Column(JSON, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    last_seen_at = Column(DateTime(timezone=True), nullable=True, index=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=_utcnow,
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=_utcnow,
        onupdate=_utcnow,
    )


Index("idx_iot_devices_org_type_status", Device.organisation_id, Device.device_type, Device.status)
Index("idx_iot_devices_org_asset", Device.organisation_id, Device.asset_id)


class DeviceHeartbeat(Base):
    __tablename__ = "iot_device_heartbeats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    organisation_id = Column(
        Integer,
        ForeignKey("organisations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    device_id = Column(
        Integer,
        ForeignKey("iot_devices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    recorded_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=_utcnow,
        index=True,
    )
    status = Column(String(32), nullable=False, default="healthy", index=True)
    battery_level = Column(Float, nullable=True)
    queue_depth = Column(Integer, nullable=True)
    signal_strength = Column(Float, nullable=True)
    details_json = Column(JSON, nullable=True)


Index("idx_iot_heartbeats_org_device_time", DeviceHeartbeat.organisation_id, DeviceHeartbeat.device_id, DeviceHeartbeat.recorded_at)


class TelemetryEvent(Base):
    __tablename__ = "iot_telemetry_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    organisation_id = Column(
        Integer,
        ForeignKey("organisations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    device_id = Column(
        Integer,
        ForeignKey("iot_devices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="SET NULL"), nullable=True, index=True)
    generated_alert_id = Column(Integer, ForeignKey("alerts.id", ondelete="SET NULL"), nullable=True, index=True)
    event_id = Column(String(128), nullable=True, index=True)
    source_type = Column(String(16), nullable=False, index=True)
    source_id = Column(String(128), nullable=False)
    telemetry_type = Column(String(32), nullable=False, index=True)
    reading_type = Column(String(64), nullable=True, index=True)
    dedupe_key = Column(String(64), nullable=False, unique=True, index=True)
    correlation_mmsi = Column(String(32), nullable=True, index=True)
    recorded_at = Column(DateTime(timezone=True), nullable=False, index=True)
    payload_json = Column(JSON, nullable=False)
    normalized_json = Column(JSON, nullable=False)
    severity_hint = Column(Integer, nullable=False, default=0)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=_utcnow,
    )


Index("idx_iot_telemetry_org_asset_time", TelemetryEvent.organisation_id, TelemetryEvent.asset_id, TelemetryEvent.recorded_at)
Index("idx_iot_telemetry_org_type_time", TelemetryEvent.organisation_id, TelemetryEvent.telemetry_type, TelemetryEvent.recorded_at)


class EdgeSyncBatch(Base):
    __tablename__ = "iot_edge_sync_batches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    organisation_id = Column(
        Integer,
        ForeignKey("organisations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    device_id = Column(
        Integer,
        ForeignKey("iot_devices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status = Column(String(32), nullable=False, default="queued", index=True)
    signature = Column(String(255), nullable=True)
    event_count = Column(Integer, nullable=False, default=0)
    payload_json = Column(JSON, nullable=False)
    uploaded_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=_utcnow,
        index=True,
    )
    replayed_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)


Index("idx_iot_edge_batches_org_device_uploaded", EdgeSyncBatch.organisation_id, EdgeSyncBatch.device_id, EdgeSyncBatch.uploaded_at)
