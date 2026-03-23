from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from math import cos, radians
from typing import Any, Optional

from app.core.config import settings
from app.infrastructure.ingest.loaders import AisPoint
from app.modules.itdae.geofences.baltic_cables import BALTIC_CABLE_ZONES
from app.tracking.features import haversine_m

FUSED_RULE_SCHEMA_VERSION = "1.0.0"
FUSED_PROVENANCE_VERSION = "2026-03-23"
SIMULATION_FIXTURE_EVENT_ID = "simulated-surface-activity-v1"


@dataclass(frozen=True)
class SurfaceActivityEvent:
    event_id: str
    source: str
    observed_at: datetime
    mmsi: str
    lat: float
    lon: float
    sog: Optional[float] = None
    cog: Optional[float] = None


def map_ais_to_surface_activity_event(point: AisPoint) -> SurfaceActivityEvent:
    return SurfaceActivityEvent(
        event_id=f"ais-{point.mmsi}-{int(point.timestamp.timestamp())}",
        source="ais",
        observed_at=point.timestamp,
        mmsi=point.mmsi,
        lat=point.lat,
        lon=point.lon,
        sog=point.sog,
        cog=point.cog,
    )


def simulation_surface_activity_fixture(anchor: AisPoint) -> SurfaceActivityEvent:
    return SurfaceActivityEvent(
        event_id=SIMULATION_FIXTURE_EVENT_ID,
        source="simulation_fixture",
        observed_at=anchor.timestamp,
        mmsi=anchor.mmsi,
        lat=anchor.lat,
        lon=anchor.lon,
        sog=anchor.sog,
        cog=anchor.cog,
    )


def _distance_point_to_segment_m(
    point_lat: float,
    point_lon: float,
    seg_lat1: float,
    seg_lon1: float,
    seg_lat2: float,
    seg_lon2: float,
) -> float:
    # Local equirectangular approximation then haversine refine at projected point.
    mean_lat_rad = radians((seg_lat1 + seg_lat2 + point_lat) / 3.0)
    x1 = seg_lon1 * cos(mean_lat_rad)
    y1 = seg_lat1
    x2 = seg_lon2 * cos(mean_lat_rad)
    y2 = seg_lat2
    xp = point_lon * cos(mean_lat_rad)
    yp = point_lat

    dx = x2 - x1
    dy = y2 - y1
    if dx == 0 and dy == 0:
        return haversine_m(point_lat, point_lon, seg_lat1, seg_lon1)

    t = ((xp - x1) * dx + (yp - y1) * dy) / (dx * dx + dy * dy)
    t_clamped = max(0.0, min(1.0, t))
    proj_x = x1 + t_clamped * dx
    proj_y = y1 + t_clamped * dy
    proj_lon = proj_x / cos(mean_lat_rad)
    proj_lat = proj_y
    return haversine_m(point_lat, point_lon, proj_lat, proj_lon)


def _nearest_cable_segment(lat: float, lon: float) -> tuple[dict[str, Any], float]:
    best: Optional[dict[str, Any]] = None
    best_dist = float("inf")
    for zone in BALTIC_CABLE_ZONES:
        polygon = zone.get("polygon") or []
        for i in range(len(polygon) - 1):
            lon1, lat1 = polygon[i]
            lon2, lat2 = polygon[i + 1]
            dist = _distance_point_to_segment_m(lat, lon, lat1, lon1, lat2, lon2)
            if dist < best_dist:
                best_dist = dist
                best = {
                    "zone_id": zone["id"],
                    "zone_name": zone["name"],
                    "risk_level": zone.get("risk_level", "unknown"),
                    "segment_index": i,
                    "segment_start": {"lat": lat1, "lon": lon1},
                    "segment_end": {"lat": lat2, "lon": lon2},
                }
    if best is None:
        raise ValueError("No cable geometry available")
    return best, best_dist


def rule_surface_activity_near_cable_segment(
    p1: AisPoint,
    p2: AisPoint,
    events: Optional[list[SurfaceActivityEvent]] = None,
) -> Optional[dict[str, Any]]:
    dt_sec = (p2.timestamp - p1.timestamp).total_seconds()
    if dt_sec <= 0:
        return None

    window_sec = getattr(settings, "fused_cable_time_window_sec", 1200)
    if dt_sec > window_sec:
        return None

    events_in = events or [map_ais_to_surface_activity_event(p2)]
    if not events_in:
        events_in = [simulation_surface_activity_fixture(p2)]
    event = events_in[0]
    segment, distance_m = _nearest_cable_segment(event.lat, event.lon)
    proximity_m = getattr(settings, "fused_cable_proximity_m", 1500.0)
    if distance_m > proximity_m:
        return None

    severity = 60
    if segment["risk_level"] == "critical":
        severity = 80
    elif segment["risk_level"] == "high":
        severity = 70

    return {
        "type": "FUSED_ACTIVITY_NEAR_CABLE",
        "severity": severity,
        "summary": (
            f"Surface activity event near cable segment "
            f"({distance_m:.0f}m <= {proximity_m:.0f}m)"
        ),
        "evidence": {
            "schema_version": FUSED_RULE_SCHEMA_VERSION,
            "provenance_version": FUSED_PROVENANCE_VERSION,
            "rule": "surface_activity_near_cable_segment",
            "time_window_sec": window_sec,
            "event": asdict(event),
            "segment": segment,
            "distance_to_segment_m": round(distance_m, 3),
            "proximity_threshold_m": proximity_m,
            "dt_sec": dt_sec,
            "simulated_event_used": event.source == "simulation_fixture",
        },
    }
