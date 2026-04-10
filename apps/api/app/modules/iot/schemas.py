from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class DeviceCreate(BaseModel):
    device_type: str = Field(..., description="gateway, sensor, collector")
    name: str
    asset_id: Optional[int] = None
    status: str = "active"
    firmware_version: Optional[str] = None
    certificate_ref: Optional[str] = None
    connectivity_profile: Optional[dict[str, Any]] = None
    location_json: Optional[dict[str, Any]] = None
    metadata_json: Optional[dict[str, Any]] = None
    is_active: bool = True


class DeviceUpdate(BaseModel):
    name: Optional[str] = None
    asset_id: Optional[int] = None
    status: Optional[str] = None
    firmware_version: Optional[str] = None
    certificate_ref: Optional[str] = None
    connectivity_profile: Optional[dict[str, Any]] = None
    location_json: Optional[dict[str, Any]] = None
    metadata_json: Optional[dict[str, Any]] = None
    is_active: Optional[bool] = None


class DeviceOut(BaseModel):
    id: int
    organisation_id: int
    asset_id: Optional[int] = None
    device_type: str
    name: str
    status: str
    firmware_version: Optional[str] = None
    certificate_ref: Optional[str] = None
    connectivity_profile: Optional[dict[str, Any]] = None
    location_json: Optional[dict[str, Any]] = None
    metadata_json: Optional[dict[str, Any]] = None
    is_active: bool
    last_seen_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class DeviceHeartbeatCreate(BaseModel):
    status: str = "healthy"
    recorded_at: Optional[datetime] = None
    battery_level: Optional[float] = None
    queue_depth: Optional[int] = None
    signal_strength: Optional[float] = None
    details_json: Optional[dict[str, Any]] = None


class DeviceHeartbeatOut(BaseModel):
    id: int
    organisation_id: int
    device_id: int
    recorded_at: datetime
    status: str
    battery_level: Optional[float] = None
    queue_depth: Optional[int] = None
    signal_strength: Optional[float] = None
    details_json: Optional[dict[str, Any]] = None


class TelemetryEnvelopeIn(BaseModel):
    event_id: Optional[str] = None
    source_type: str = Field(..., description="mqtt, nmea, edge_batch, api")
    source_id: Optional[str] = None
    recorded_at: Optional[datetime] = None
    dedupe_key: Optional[str] = None
    payload: dict[str, Any]


class MqttIngestRequest(BaseModel):
    topic: str
    payload: dict[str, Any] | str
    device_id: Optional[int] = None
    recorded_at: Optional[datetime] = None
    event_id: Optional[str] = None


class NmeaIngestRequest(BaseModel):
    sentence: str
    device_id: Optional[int] = None
    source_id: Optional[str] = None
    recorded_at: Optional[datetime] = None


class TelemetryEventOut(BaseModel):
    id: int
    organisation_id: int
    device_id: int
    asset_id: Optional[int] = None
    generated_alert_id: Optional[int] = None
    event_id: Optional[str] = None
    source_type: str
    source_id: str
    telemetry_type: str
    reading_type: Optional[str] = None
    dedupe_key: str
    correlation_mmsi: Optional[str] = None
    recorded_at: datetime
    payload_json: dict[str, Any]
    normalized_json: dict[str, Any]
    severity_hint: int
    created_at: datetime


class EdgeBatchCreate(BaseModel):
    signature: Optional[str] = None
    events: list[TelemetryEnvelopeIn]


class EdgeBatchOut(BaseModel):
    id: int
    organisation_id: int
    device_id: int
    status: str
    signature: Optional[str] = None
    event_count: int
    payload_json: dict[str, Any]
    uploaded_at: datetime
    replayed_at: Optional[datetime] = None
    last_error: Optional[str] = None


class EdgeBatchReplayOut(BaseModel):
    batch: EdgeBatchOut
    processed_events: int
    generated_alert_ids: list[int] = []


class AssetRiskSummaryOut(BaseModel):
    asset_id: int
    asset_name: str
    asset_type: str
    criticality: str
    risk_score: int
    active_alerts: int
    active_incidents: int
    maintenance_active: bool


class DeviceHealthSummaryOut(BaseModel):
    device_id: int
    device_name: str
    asset_id: Optional[int] = None
    asset_name: Optional[str] = None
    status: str
    last_seen_at: Optional[datetime] = None
    latest_queue_depth: Optional[int] = None
    latest_signal_strength: Optional[float] = None


class IotOverviewOut(BaseModel):
    generated_at: datetime
    recent_telemetry_count: int
    queued_edge_batches: int
    open_incident_count: int
    active_alert_count: int
    assets: list[AssetRiskSummaryOut]
    devices: list[DeviceHealthSummaryOut]
    recent_events: list[TelemetryEventOut]
