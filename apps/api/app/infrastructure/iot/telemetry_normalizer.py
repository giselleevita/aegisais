from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _stable_hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


def _coerce_payload(payload: dict[str, Any] | str) -> dict[str, Any]:
    if isinstance(payload, dict):
        return payload
    try:
        decoded = json.loads(payload)
    except json.JSONDecodeError:
        return {"raw": payload}
    return decoded if isinstance(decoded, dict) else {"value": decoded}


def normalize_mqtt_payload(
    *,
    topic: str,
    payload: dict[str, Any] | str,
    device_id: int | None = None,
    recorded_at: datetime | None = None,
    event_id: str | None = None,
) -> dict[str, Any]:
    raw_payload = _coerce_payload(payload)
    timestamp = recorded_at or _now_utc()
    location = raw_payload.get("location") or {
        "lat": raw_payload.get("lat"),
        "lon": raw_payload.get("lon"),
    }
    normalized = {
        "event_id": event_id or raw_payload.get("event_id") or str(uuid.uuid4()),
        "source_type": "mqtt",
        "source_id": raw_payload.get("source_id") or f"mqtt:{topic}",
        "recorded_at": timestamp,
        "telemetry_type": raw_payload.get("telemetry_type") or raw_payload.get("type") or "sensor_reading",
        "reading_type": raw_payload.get("reading_type") or raw_payload.get("metric") or "generic",
        "value": raw_payload.get("value"),
        "unit": raw_payload.get("unit"),
        "threshold": raw_payload.get("threshold"),
        "health_state": raw_payload.get("health_state") or raw_payload.get("status"),
        "queue_depth": raw_payload.get("queue_depth"),
        "battery_level": raw_payload.get("battery_level"),
        "signal_strength": raw_payload.get("signal_strength"),
        "location": location,
        "mmsi": raw_payload.get("mmsi"),
        "topic": topic,
        "payload": raw_payload,
        "device_id": device_id,
    }
    dedupe_material = {
        "source": normalized["source_id"],
        "recorded_at": timestamp.isoformat(),
        "reading_type": normalized["reading_type"],
        "value": normalized["value"],
        "device_id": device_id,
    }
    normalized["dedupe_key"] = raw_payload.get("dedupe_key") or _stable_hash(dedupe_material)
    return normalized


def _nmea_latlon_to_decimal(value: str, direction: str) -> float:
    if not value:
        raise ValueError("Missing NMEA coordinate")
    split_at = 2 if direction in {"N", "S"} else 3
    degrees = float(value[:split_at])
    minutes = float(value[split_at:])
    decimal = degrees + minutes / 60.0
    if direction in {"S", "W"}:
        decimal *= -1
    return decimal


def normalize_nmea_sentence(
    *,
    sentence: str,
    device_id: int | None = None,
    recorded_at: datetime | None = None,
    source_id: str | None = None,
) -> dict[str, Any]:
    if not sentence.startswith("$"):
        raise ValueError("Unsupported NMEA sentence")

    timestamp = recorded_at or _now_utc()
    parts = sentence.strip().split(",")
    message_type = parts[0][3:]
    if message_type != "RMC":
        raise ValueError("Only RMC NMEA sentences are currently supported")

    lat = _nmea_latlon_to_decimal(parts[3], parts[4])
    lon = _nmea_latlon_to_decimal(parts[5], parts[6])
    sog = float(parts[7] or 0)
    cog = float(parts[8] or 0)
    payload = {
        "sentence": sentence,
        "lat": lat,
        "lon": lon,
        "sog": sog,
        "cog": cog,
        "status": parts[2],
    }
    normalized = {
        "event_id": str(uuid.uuid4()),
        "source_type": "nmea",
        "source_id": source_id or f"nmea:{message_type}",
        "recorded_at": timestamp,
        "telemetry_type": "vessel_position",
        "reading_type": "position_fix",
        "value": sog,
        "unit": "knots",
        "threshold": None,
        "health_state": None,
        "queue_depth": None,
        "battery_level": None,
        "signal_strength": None,
        "location": {"lat": lat, "lon": lon},
        "mmsi": payload.get("mmsi"),
        "topic": None,
        "payload": payload,
        "device_id": device_id,
    }
    normalized["dedupe_key"] = _stable_hash(
        {
            "source": normalized["source_id"],
            "recorded_at": timestamp.isoformat(),
            "lat": lat,
            "lon": lon,
            "sog": sog,
            "cog": cog,
            "device_id": device_id,
        }
    )
    return normalized