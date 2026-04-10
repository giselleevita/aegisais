from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.modules.assets.models import Asset
from app.modules.assets.service import asset_has_active_maintenance_window
from app.modules.iot.models import TelemetryEvent
from app.modules.vessels.models import VesselLatest
from app.tracking.features import haversine_m


def _asset_centroid(asset: Asset | None) -> tuple[float | None, float | None]:
    if asset is None or not asset.geometry_json:
        return None, None
    geometry_type = asset.geometry_json.get("type")
    coordinates = asset.geometry_json.get("coordinates")
    if geometry_type == "Point" and isinstance(coordinates, list) and len(coordinates) >= 2:
        return float(coordinates[1]), float(coordinates[0])
    if geometry_type == "LineString" and isinstance(coordinates, list) and coordinates:
        lon = sum(point[0] for point in coordinates) / len(coordinates)
        lat = sum(point[1] for point in coordinates) / len(coordinates)
        return float(lat), float(lon)
    return None, None


def _nearest_vessel(db: Session, organisation_id: int, lat: float | None, lon: float | None) -> tuple[VesselLatest | None, float | None]:
    if lat is None or lon is None:
        return None, None
    nearest: VesselLatest | None = None
    nearest_distance: float | None = None
    rows = db.query(VesselLatest).filter(VesselLatest.organisation_id == organisation_id).all()
    for row in rows:
        distance = haversine_m(lat, lon, row.lat, row.lon)
        if nearest_distance is None or distance < nearest_distance:
            nearest = row
            nearest_distance = distance
    return nearest, nearest_distance


def build_fusion_alert(db: Session, event: TelemetryEvent) -> dict[str, Any] | None:
    normalized = event.normalized_json or {}
    asset = db.query(Asset).filter(Asset.id == event.asset_id).first() if event.asset_id else None
    lat, lon = _asset_centroid(asset)
    location = normalized.get("location") or {}
    lat = location.get("lat", lat)
    lon = location.get("lon", lon)

    nearest_vessel, nearest_distance = _nearest_vessel(db, event.organisation_id, lat, lon)
    maintenance_active = bool(event.asset_id) and asset_has_active_maintenance_window(db, event.asset_id)
    reading_type = event.reading_type or normalized.get("reading_type") or "generic"
    value = normalized.get("value")
    threshold = normalized.get("threshold")
    queue_depth = normalized.get("queue_depth")
    health_state = normalized.get("health_state")

    alert_type: str | None = None
    severity = 0
    summary = ""

    if reading_type in {"tamper", "hatch_open", "device_open"} or normalized.get("tamper_detected") is True:
        alert_type = "SENSOR_TAMPER"
        severity = 92
        summary = f"Sensor tamper signal detected on device {event.device_id}"
    elif health_state in {"degraded", "offline"} or (queue_depth is not None and int(queue_depth) >= 50):
        alert_type = "EDGE_GATEWAY_DEGRADED"
        severity = 68 if health_state == "degraded" else 78
        summary = f"Edge gateway degradation detected on device {event.device_id}"
    elif value is not None and threshold is not None and float(value) >= float(threshold):
        if nearest_vessel is not None and nearest_distance is not None and nearest_distance <= 10_000:
            alert_type = "CORROBORATED_VESSEL_PROXIMITY"
            severity = 86 if nearest_distance <= 5_000 else 78
            summary = f"Sensor anomaly corroborated by nearby vessel {nearest_vessel.mmsi}"
        else:
            alert_type = "CABLE_ENVIRONMENTAL_CHANGE"
            severity = 72
            summary = f"Sensor reading exceeded threshold for asset {event.asset_id}"

    if alert_type is None:
        return None
    if maintenance_active and alert_type not in {"SENSOR_TAMPER", "EDGE_GATEWAY_DEGRADED"}:
        return None

    mmsi = nearest_vessel.mmsi if nearest_vessel is not None else f"device:{event.device_id}"
    evidence = {
        "telemetry_event_id": event.id,
        "asset_id": event.asset_id,
        "device_id": event.device_id,
        "source_type": event.source_type,
        "telemetry_type": event.telemetry_type,
        "reading_type": reading_type,
        "value": value,
        "threshold": threshold,
        "health_state": health_state,
        "queue_depth": queue_depth,
        "location": {"lat": lat, "lon": lon},
        "maintenance_active": maintenance_active,
        "nearest_vessel_mmsi": nearest_vessel.mmsi if nearest_vessel is not None else None,
        "nearest_vessel_distance_m": nearest_distance,
        "recorded_at": event.recorded_at.isoformat(),
    }
    return {
        "mmsi": mmsi,
        "type": alert_type,
        "severity": severity,
        "summary": summary,
        "evidence": evidence,
    }