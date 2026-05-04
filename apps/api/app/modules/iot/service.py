from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, cast

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.assets.models import Asset
from app.modules.assets.service import asset_has_active_maintenance_window
from app.modules.audit.services import AuditService
from app.modules.auth.models import User
from app.modules.auth.org_scope import apply_org_filter
from app.modules.alerts.models import Alert, derive_alert_idempotency_key, derive_evidence_hash
from app.detection.iot_fusion import build_fusion_alert
from app.modules.incidents.models import Incident
from app.modules.incidents.service import create_incident_from_alert_with_flag
from app.modules.iot.models import Device, DeviceHeartbeat, EdgeSyncBatch, TelemetryEvent
from app.modules.iot.schemas import (
    DeviceCreate,
    DeviceHeartbeatCreate,
    DeviceHeartbeatOut,
    DeviceOut,
    DeviceUpdate,
    EdgeBatchCreate,
    EdgeBatchOut,
    EdgeBatchReplayOut,
    IotOverviewOut,
    DeviceHealthSummaryOut,
    AssetRiskSummaryOut,
    MqttIngestRequest,
    NmeaIngestRequest,
    TelemetryEnvelopeIn,
    TelemetryEventOut,
)
from app.infrastructure.iot.telemetry_normalizer import normalize_mqtt_payload, normalize_nmea_sentence


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _device_to_out(device: Device) -> DeviceOut:
    return DeviceOut(
        id=cast(int, device.id),
        organisation_id=cast(int, device.organisation_id),
        asset_id=cast(int | None, device.asset_id),
        device_type=cast(str, device.device_type),
        name=cast(str, device.name),
        status=cast(str, device.status),
        firmware_version=cast(str | None, device.firmware_version),
        certificate_ref=cast(str | None, device.certificate_ref),
        connectivity_profile=cast(dict[str, Any] | None, device.connectivity_profile),
        location_json=cast(dict[str, Any] | None, device.location_json),
        metadata_json=cast(dict[str, Any] | None, device.metadata_json),
        is_active=cast(bool, device.is_active),
        last_seen_at=cast(datetime | None, device.last_seen_at),
        revoked_at=cast(datetime | None, device.revoked_at),
        created_at=cast(datetime, device.created_at),
        updated_at=cast(datetime, device.updated_at),
    )


def _heartbeat_to_out(heartbeat: DeviceHeartbeat) -> DeviceHeartbeatOut:
    return DeviceHeartbeatOut(
        id=cast(int, heartbeat.id),
        organisation_id=cast(int, heartbeat.organisation_id),
        device_id=cast(int, heartbeat.device_id),
        recorded_at=cast(datetime, heartbeat.recorded_at),
        status=cast(str, heartbeat.status),
        battery_level=cast(float | None, heartbeat.battery_level),
        queue_depth=cast(int | None, heartbeat.queue_depth),
        signal_strength=cast(float | None, heartbeat.signal_strength),
        details_json=cast(dict[str, Any] | None, heartbeat.details_json),
    )


def _telemetry_to_out(event: TelemetryEvent) -> TelemetryEventOut:
    return TelemetryEventOut(
        id=cast(int, event.id),
        organisation_id=cast(int, event.organisation_id),
        device_id=cast(int, event.device_id),
        asset_id=cast(int | None, event.asset_id),
        generated_alert_id=cast(int | None, event.generated_alert_id),
        event_id=cast(str | None, event.event_id),
        source_type=cast(str, event.source_type),
        source_id=cast(str, event.source_id),
        telemetry_type=cast(str, event.telemetry_type),
        reading_type=cast(str | None, event.reading_type),
        dedupe_key=cast(str, event.dedupe_key),
        correlation_mmsi=cast(str | None, event.correlation_mmsi),
        recorded_at=cast(datetime, event.recorded_at),
        payload_json=cast(dict[str, Any], event.payload_json or {}),
        normalized_json=cast(dict[str, Any], event.normalized_json or {}),
        severity_hint=cast(int, event.severity_hint),
        created_at=cast(datetime, event.created_at),
    )


def _edge_batch_to_out(batch: EdgeSyncBatch) -> EdgeBatchOut:
    return EdgeBatchOut(
        id=cast(int, batch.id),
        organisation_id=cast(int, batch.organisation_id),
        device_id=cast(int, batch.device_id),
        status=cast(str, batch.status),
        signature=cast(str | None, batch.signature),
        event_count=cast(int, batch.event_count),
        payload_json=cast(dict[str, Any], batch.payload_json or {}),
        uploaded_at=cast(datetime, batch.uploaded_at),
        replayed_at=cast(datetime | None, batch.replayed_at),
        last_error=cast(str | None, batch.last_error),
    )


def _ensure_asset_visible(db: Session, asset_id: int, actor: User) -> None:
    asset = apply_org_filter(db.query(Asset).filter(Asset.id == asset_id), Asset, actor).first()
    if asset is None:
        raise HTTPException(status_code=404, detail="Linked asset not found")


def _resolve_device(db: Session, device_id: int, actor: User) -> Device:
    device = apply_org_filter(db.query(Device).filter(Device.id == device_id), Device, actor).first()
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


def _persist_fusion_alert(db: Session, event: TelemetryEvent, *, actor_username: str) -> int | None:
    fusion_alert = build_fusion_alert(db, event)
    if fusion_alert is None:
        return None

    alert = Alert(
        organisation_id=event.organisation_id,
        asset_id=event.asset_id,
        source_device_id=event.device_id,
        timestamp=event.recorded_at,
        mmsi=cast(str, fusion_alert["mmsi"]),
        type=cast(str, fusion_alert["type"]),
        severity=cast(int, fusion_alert["severity"]),
        summary=cast(str, fusion_alert["summary"]),
        evidence=cast(dict[str, Any], fusion_alert["evidence"]),
        evidence_hash=derive_evidence_hash(cast(dict[str, Any], fusion_alert["evidence"])),
        idempotency_key=derive_alert_idempotency_key(
            cast(int, event.organisation_id),
            cast(str, fusion_alert["mmsi"]),
            cast(str, fusion_alert["type"]),
            event.recorded_at,
        ),
        status="new",
    )
    try:
        db.add(alert)
        db.flush()
    except IntegrityError:
        db.rollback()
        existing = db.query(Alert).filter(Alert.idempotency_key == alert.idempotency_key).first()
        return cast(int | None, existing.id if existing is not None else None)

    event.generated_alert_id = alert.id
    AuditService.log_event(
        db,
        action="iot.fusion.alert.create",
        change_summary=f"Created fused IoT alert {alert.type}",
        organisation_id=cast(int, event.organisation_id),
        user_id=actor_username,
        resource_id=str(alert.id),
        resource_type="alert",
        details={"telemetry_event_id": event.id, "device_id": event.device_id, "asset_id": event.asset_id},
    )
    if alert.severity >= 80:
        incident, created = create_incident_from_alert_with_flag(db, alert)
        if created:
            AuditService.log_event(
                db,
                action="incident.create.system",
                change_summary=f"Created IoT incident from alert {alert.id}",
                organisation_id=cast(int, alert.organisation_id),
                user_id="system:iot_fusion",
                resource_id=str(incident.id),
                resource_type="incident",
                details={"alert_id": alert.id, "asset_id": alert.asset_id, "mmsi": alert.mmsi, "alert_type": alert.type},
                correlation_id=event.dedupe_key,
            )
    return cast(int, alert.id)


def _persist_telemetry_event(db: Session, normalized: dict[str, Any], *, actor: User, source_payload: dict[str, Any]) -> TelemetryEvent:
    if normalized.get("device_id") is None:
        raise HTTPException(status_code=400, detail="Telemetry payload must resolve to a device")
    device = _resolve_device(db, int(normalized["device_id"]), actor)
    recorded_at_value = normalized["recorded_at"]
    if isinstance(recorded_at_value, str):
        recorded_at_value = datetime.fromisoformat(recorded_at_value.replace("Z", "+00:00"))
    event = TelemetryEvent(
        organisation_id=device.organisation_id,
        device_id=device.id,
        asset_id=device.asset_id,
        event_id=normalized.get("event_id"),
        source_type=normalized["source_type"],
        source_id=normalized["source_id"],
        telemetry_type=normalized["telemetry_type"],
        reading_type=normalized.get("reading_type"),
        dedupe_key=normalized["dedupe_key"],
        correlation_mmsi=normalized.get("mmsi"),
        recorded_at=recorded_at_value,
        payload_json=source_payload,
        normalized_json=normalized,
        severity_hint=int(normalized.get("threshold") is not None and normalized.get("value") is not None and float(normalized["value"]) >= float(normalized["threshold"]) and 70 or 0),
    )
    try:
        db.add(event)
        db.flush()
    except IntegrityError:
        db.rollback()
        existing = db.query(TelemetryEvent).filter(TelemetryEvent.dedupe_key == normalized["dedupe_key"]).first()
        if existing is None:
            raise
        return existing

    AuditService.log_event(
        db,
        action="iot.telemetry.ingest",
        change_summary=f"Ingested telemetry event {event.source_type}:{event.telemetry_type}",
        organisation_id=cast(int, device.organisation_id),
        user_id=cast(str, actor.username),
        resource_id=str(event.id),
        resource_type="iot_telemetry",
        details={"device_id": device.id, "asset_id": device.asset_id, "dedupe_key": event.dedupe_key},
        correlation_id=event.dedupe_key,
    )
    alert_id = _persist_fusion_alert(db, event, actor_username=cast(str, actor.username))
    if alert_id is not None:
        event.generated_alert_id = alert_id
    db.commit()
    db.refresh(event)
    return event


def create_device(db: Session, body: DeviceCreate, *, actor: User) -> DeviceOut:
    if body.asset_id is not None:
        _ensure_asset_visible(db, body.asset_id, actor)
    device = Device(
        organisation_id=actor.organisation_id,
        asset_id=body.asset_id,
        created_by_id=actor.id,
        device_type=body.device_type,
        name=body.name,
        status=body.status,
        firmware_version=body.firmware_version,
        certificate_ref=body.certificate_ref,
        connectivity_profile=body.connectivity_profile,
        location_json=body.location_json,
        metadata_json=body.metadata_json,
        is_active=body.is_active,
    )
    db.add(device)
    db.flush()
    AuditService.log_event(
        db,
        action="iot.device.create",
        change_summary=f"Created IoT device {device.name}",
        organisation_id=cast(int, actor.organisation_id),
        user_id=cast(str, actor.username),
        resource_id=str(device.id),
        resource_type="iot_device",
        details={"device_type": body.device_type, "asset_id": body.asset_id},
    )
    db.commit()
    db.refresh(device)
    return _device_to_out(device)


def list_devices(
    db: Session,
    *,
    user: User,
    device_type: str | None = None,
    status: str | None = None,
    asset_id: int | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[DeviceOut]:
    query = apply_org_filter(db.query(Device), Device, user)
    if device_type:
        query = query.filter(Device.device_type == device_type)
    if status:
        query = query.filter(Device.status == status)
    if asset_id is not None:
        query = query.filter(Device.asset_id == asset_id)
    rows = query.order_by(Device.last_seen_at.desc().nullslast(), Device.id.desc()).offset(offset).limit(limit).all()
    return [_device_to_out(row) for row in rows]


def get_device(db: Session, device_id: int, *, user: User) -> DeviceOut:
    query = apply_org_filter(db.query(Device).filter(Device.id == device_id), Device, user)
    row = query.first()
    if row is None:
        raise HTTPException(status_code=404, detail="Device not found")
    return _device_to_out(row)


def update_device(db: Session, device_id: int, body: DeviceUpdate, *, actor: User) -> DeviceOut:
    query = apply_org_filter(db.query(Device).filter(Device.id == device_id), Device, actor)
    row = query.first()
    if row is None:
        raise HTTPException(status_code=404, detail="Device not found")
    if body.asset_id is not None:
        _ensure_asset_visible(db, body.asset_id, actor)

    changed: dict[str, dict[str, Any]] = {}
    for field in (
        "name",
        "asset_id",
        "status",
        "firmware_version",
        "certificate_ref",
        "connectivity_profile",
        "location_json",
        "metadata_json",
        "is_active",
    ):
        value = getattr(body, field)
        if value is not None and value != getattr(row, field):
            changed[field] = {"from": getattr(row, field), "to": value}
            setattr(row, field, value)
    if body.status == "revoked" and row.revoked_at is None:
        row.revoked_at = _now_utc()
    row.updated_at = _now_utc()

    if changed:
        AuditService.log_event(
            db,
            action="iot.device.update",
            change_summary=f"Updated IoT device {device_id}",
            organisation_id=cast(int, row.organisation_id),
            user_id=cast(str, actor.username),
            resource_id=str(device_id),
            resource_type="iot_device",
            details={"changes": changed},
        )

    db.commit()
    db.refresh(row)
    return _device_to_out(row)


def create_heartbeat(db: Session, device_id: int, body: DeviceHeartbeatCreate, *, actor: User) -> DeviceHeartbeatOut:
    device = apply_org_filter(db.query(Device).filter(Device.id == device_id), Device, actor).first()
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")
    recorded_at = body.recorded_at or _now_utc()
    heartbeat = DeviceHeartbeat(
        organisation_id=device.organisation_id,
        device_id=device_id,
        recorded_at=recorded_at,
        status=body.status,
        battery_level=body.battery_level,
        queue_depth=body.queue_depth,
        signal_strength=body.signal_strength,
        details_json=body.details_json,
    )
    device.last_seen_at = recorded_at
    device.status = body.status
    device.updated_at = _now_utc()
    db.add(heartbeat)
    db.flush()
    AuditService.log_event(
        db,
        action="iot.device.heartbeat",
        change_summary=f"Recorded heartbeat for IoT device {device_id}",
        organisation_id=cast(int, device.organisation_id),
        user_id=cast(str, actor.username),
        resource_id=str(heartbeat.id),
        resource_type="iot_device_heartbeat",
        details={"status": body.status, "queue_depth": body.queue_depth},
    )
    db.commit()
    db.refresh(heartbeat)
    return _heartbeat_to_out(heartbeat)


def list_heartbeats(db: Session, device_id: int, *, user: User, limit: int = 100) -> list[DeviceHeartbeatOut]:
    device = apply_org_filter(db.query(Device).filter(Device.id == device_id), Device, user).first()
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")
    rows = (
        apply_org_filter(db.query(DeviceHeartbeat).filter(DeviceHeartbeat.device_id == device_id), DeviceHeartbeat, user)
        .order_by(DeviceHeartbeat.recorded_at.desc())
        .limit(limit)
        .all()
    )
    return [_heartbeat_to_out(row) for row in rows]


def ingest_mqtt_telemetry(db: Session, body: MqttIngestRequest, *, actor: User) -> TelemetryEventOut:
    normalized = normalize_mqtt_payload(
        topic=body.topic,
        payload=body.payload,
        device_id=body.device_id,
        recorded_at=body.recorded_at,
        event_id=body.event_id,
    )
    event = _persist_telemetry_event(
        db,
        normalized,
        actor=actor,
        source_payload=body.payload if isinstance(body.payload, dict) else {"raw": body.payload},
    )
    return _telemetry_to_out(event)


def ingest_nmea_telemetry(db: Session, body: NmeaIngestRequest, *, actor: User) -> TelemetryEventOut:
    normalized = normalize_nmea_sentence(
        sentence=body.sentence,
        device_id=body.device_id,
        source_id=body.source_id,
        recorded_at=body.recorded_at,
    )
    event = _persist_telemetry_event(db, normalized, actor=actor, source_payload={"sentence": body.sentence})
    return _telemetry_to_out(event)


def ingest_telemetry_envelope(db: Session, body: TelemetryEnvelopeIn, *, device_id: int, actor: User) -> TelemetryEventOut:
    normalized = {
        "event_id": body.event_id,
        "source_type": body.source_type,
        "source_id": body.source_id or f"{body.source_type}:device:{device_id}",
        "recorded_at": (body.recorded_at or _now_utc()).isoformat(),
        "telemetry_type": body.payload.get("telemetry_type", "sensor_reading"),
        "reading_type": body.payload.get("reading_type", "generic"),
        "value": body.payload.get("value"),
        "unit": body.payload.get("unit"),
        "threshold": body.payload.get("threshold"),
        "health_state": body.payload.get("health_state"),
        "queue_depth": body.payload.get("queue_depth"),
        "battery_level": body.payload.get("battery_level"),
        "signal_strength": body.payload.get("signal_strength"),
        "location": body.payload.get("location") or {"lat": body.payload.get("lat"), "lon": body.payload.get("lon")},
        "mmsi": body.payload.get("mmsi"),
        "topic": body.payload.get("topic"),
        "payload": body.payload,
        "device_id": device_id,
        "dedupe_key": body.dedupe_key or normalize_mqtt_payload(topic=f"api/device/{device_id}", payload=body.payload, device_id=device_id, recorded_at=body.recorded_at).get("dedupe_key"),
    }
    event = _persist_telemetry_event(db, normalized, actor=actor, source_payload=body.payload)
    return _telemetry_to_out(event)


def create_edge_batch(db: Session, device_id: int, body: EdgeBatchCreate, *, actor: User) -> EdgeBatchOut:
    device = _resolve_device(db, device_id, actor)
    batch = EdgeSyncBatch(
        organisation_id=device.organisation_id,
        device_id=device.id,
        status="queued",
        signature=body.signature,
        event_count=len(body.events),
        payload_json={"events": [event.model_dump(mode="json") for event in body.events]},
    )
    db.add(batch)
    db.flush()
    AuditService.log_event(
        db,
        action="iot.edge.batch.queue",
        change_summary=f"Queued edge batch {batch.id} for replay",
        organisation_id=cast(int, device.organisation_id),
        user_id=cast(str, actor.username),
        resource_id=str(batch.id),
        resource_type="iot_edge_batch",
        details={"device_id": device.id, "event_count": len(body.events)},
    )
    db.commit()
    db.refresh(batch)
    return _edge_batch_to_out(batch)


def replay_edge_batch(db: Session, batch_id: int, *, actor: User) -> EdgeBatchReplayOut:
    batch = db.query(EdgeSyncBatch).filter(EdgeSyncBatch.id == batch_id).first()
    if batch is None:
        raise HTTPException(status_code=404, detail="Edge batch not found")
    _resolve_device(db, batch.device_id, actor)
    events = cast(list[dict[str, Any]], (batch.payload_json or {}).get("events", []))
    generated_alert_ids: list[int] = []
    processed = 0
    batch.status = "replaying"
    db.flush()
    for raw_event in events:
        envelope = TelemetryEnvelopeIn.model_validate(raw_event)
        telemetry_event = ingest_telemetry_envelope(db, envelope, device_id=batch.device_id, actor=actor)
        processed += 1
        if telemetry_event.generated_alert_id is not None:
            generated_alert_ids.append(telemetry_event.generated_alert_id)
    batch.status = "replayed"
    batch.replayed_at = _now_utc()
    AuditService.log_event(
        db,
        action="iot.edge.batch.replay",
        change_summary=f"Replayed edge batch {batch.id}",
        organisation_id=cast(int, batch.organisation_id),
        user_id=cast(str, actor.username),
        resource_id=str(batch.id),
        resource_type="iot_edge_batch",
        details={"processed_events": processed, "generated_alerts": generated_alert_ids},
    )
    db.commit()
    db.refresh(batch)
    return EdgeBatchReplayOut(batch=_edge_batch_to_out(batch), processed_events=processed, generated_alert_ids=generated_alert_ids)


def list_telemetry_events(
    db: Session,
    *,
    user: User,
    device_id: int | None = None,
    asset_id: int | None = None,
    limit: int = 100,
) -> list[TelemetryEventOut]:
    query = apply_org_filter(db.query(TelemetryEvent), TelemetryEvent, user)
    if device_id is not None:
        query = query.filter(TelemetryEvent.device_id == device_id)
    if asset_id is not None:
        query = query.filter(TelemetryEvent.asset_id == asset_id)
    rows = query.order_by(TelemetryEvent.recorded_at.desc()).limit(limit).all()
    return [_telemetry_to_out(row) for row in rows]


def get_iot_overview(db: Session, *, user: User, limit: int = 10) -> IotOverviewOut:
    asset_rows = apply_org_filter(db.query(Asset), Asset, user).order_by(Asset.criticality.desc(), Asset.id.desc()).limit(limit).all()
    assets: list[AssetRiskSummaryOut] = []
    for asset in asset_rows:
        active_alerts = (
            apply_org_filter(db.query(Alert).filter(Alert.asset_id == asset.id, Alert.status.in_(["new", "reviewed"])), Alert, user)
            .count()
        )
        active_incidents = (
            apply_org_filter(db.query(Incident).filter(Incident.asset_id == asset.id, Incident.status.in_(["open", "monitoring"])), Incident, user)
            .count()
        )
        telemetry_hint = (
            apply_org_filter(db.query(func.max(TelemetryEvent.severity_hint)).filter(TelemetryEvent.asset_id == asset.id), TelemetryEvent, user)
            .scalar()
            or 0
        )
        risk_score = min(100, int(max(active_alerts * 15, active_incidents * 20, telemetry_hint)))
        assets.append(
            AssetRiskSummaryOut(
                asset_id=cast(int, asset.id),
                asset_name=cast(str, asset.name),
                asset_type=cast(str, asset.asset_type),
                criticality=cast(str, asset.criticality),
                risk_score=risk_score,
                active_alerts=active_alerts,
                active_incidents=active_incidents,
                maintenance_active=asset_has_active_maintenance_window(db, cast(int, asset.id)),
            )
        )

    device_rows = apply_org_filter(db.query(Device), Device, user).order_by(Device.last_seen_at.desc().nullslast(), Device.id.desc()).limit(limit).all()
    devices: list[DeviceHealthSummaryOut] = []
    asset_map = {cast(int, asset.id): cast(str, asset.name) for asset in asset_rows if asset.id is not None}
    for device in device_rows:
        heartbeat = (
            apply_org_filter(db.query(DeviceHeartbeat).filter(DeviceHeartbeat.device_id == device.id), DeviceHeartbeat, user)
            .order_by(DeviceHeartbeat.recorded_at.desc())
            .first()
        )
        devices.append(
            DeviceHealthSummaryOut(
                device_id=cast(int, device.id),
                device_name=cast(str, device.name),
                asset_id=cast(int | None, device.asset_id),
                asset_name=asset_map.get(cast(int, device.asset_id)) if device.asset_id is not None else None,
                status=cast(str, device.status),
                last_seen_at=cast(datetime | None, device.last_seen_at),
                latest_queue_depth=cast(int | None, heartbeat.queue_depth if heartbeat is not None else None),
                latest_signal_strength=cast(float | None, heartbeat.signal_strength if heartbeat is not None else None),
            )
        )

    recent_events = list_telemetry_events(db, user=user, limit=limit)
    recent_telemetry_count = apply_org_filter(db.query(TelemetryEvent), TelemetryEvent, user).count()
    queued_edge_batches = apply_org_filter(db.query(EdgeSyncBatch).filter(EdgeSyncBatch.status.in_(["queued", "replaying"])), EdgeSyncBatch, user).count()
    open_incident_count = apply_org_filter(db.query(Incident).filter(Incident.status.in_(["open", "monitoring"])), Incident, user).count()
    active_alert_count = apply_org_filter(db.query(Alert).filter(Alert.status.in_(["new", "reviewed"])), Alert, user).count()
    return IotOverviewOut(
        generated_at=_now_utc(),
        recent_telemetry_count=recent_telemetry_count,
        queued_edge_batches=queued_edge_batches,
        open_incident_count=open_incident_count,
        active_alert_count=active_alert_count,
        assets=assets,
        devices=devices,
        recent_events=recent_events,
    )
