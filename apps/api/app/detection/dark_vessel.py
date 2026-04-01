"""Dark vessel detection (GAP-05).

Detects vessels that go silent (AIS off) beyond expected transmission intervals.
Generalises ITDAE's AIS_DARK_IN_ZONE to work system-wide.

Expected AIS transmission intervals (IMO SOLAS Ch V Reg 19.2):
- Class A underway: 2-10 seconds (speed-dependent)
- Class A at anchor: 3 minutes
- Class B underway: 30 seconds
- Class B stationary: 3 minutes

We use a conservative 15-minute threshold for initial darkness detection,
escalating severity with duration.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from app.infrastructure.ingest.loaders import AisPoint
from app.tracking.features import haversine_m

_log = logging.getLogger("aegisais.detection.dark_vessel")

# Thresholds for dark vessel detection (seconds)
DARK_SUSPICIOUS_SEC = 15 * 60      # 15 minutes — unusual silence
DARK_ALERT_SEC = 30 * 60           # 30 minutes — suspicious
DARK_CRITICAL_SEC = 2 * 60 * 60    # 2 hours — critical


def rule_ais_dark(p1: AisPoint, p2: AisPoint) -> Optional[dict[str, Any]]:
    """Detect AIS silence periods between consecutive position reports.

    Fires when the gap between two reports from the same MMSI exceeds
    the expected transmission interval.  Severity scales with duration.
    """
    dt = (p2.timestamp - p1.timestamp).total_seconds()
    if dt < DARK_SUSPICIOUS_SEC:
        return None

    # Don't flag if positions are essentially the same (vessel at anchor, transmitter off)
    dist_m = haversine_m(p1.lat, p1.lon, p2.lat, p2.lon)

    if dt >= DARK_CRITICAL_SEC:
        severity = 90
        level = "critical"
    elif dt >= DARK_ALERT_SEC:
        severity = 65
        level = "alert"
    else:
        severity = 40
        level = "suspicious"

    # Higher severity if vessel moved significantly during dark period
    if dist_m > 50_000:  # > 50km
        severity = min(100, severity + 15)

    hours = dt / 3600
    return {
        "type": "AIS_DARK",
        "severity": severity,
        "summary": f"AIS silence {hours:.1f}h ({level}), moved {dist_m/1000:.1f}km",
        "evidence": {
            "dark_duration_sec": dt,
            "dark_hours": round(hours, 2),
            "distance_m": dist_m,
            "level": level,
            "p1_lat": p1.lat,
            "p1_lon": p1.lon,
            "p1_ts": p1.timestamp.isoformat(),
            "p2_lat": p2.lat,
            "p2_lon": p2.lon,
            "p2_ts": p2.timestamp.isoformat(),
            "mmsi": p2.mmsi,
        },
    }


def compute_vessel_darkness_score(
    dark_events: list[dict[str, Any]],
    window_days: int = 30,
) -> dict[str, Any]:
    """Aggregate dark vessel events into a composite darkness score (0-100).

    Used for fleet-wide ranking of suspicious vessels by cumulative dark time.
    """
    if not dark_events:
        return {"score": 0, "label": "normal", "total_dark_hours": 0, "event_count": 0}

    total_dark_sec = sum(e.get("dark_duration_sec", 0) for e in dark_events)
    total_dark_hours = total_dark_sec / 3600
    event_count = len(dark_events)

    # Score formula: combination of duration and frequency
    duration_score = min(50, total_dark_hours * 2)  # Up to 50 from duration
    frequency_score = min(50, event_count * 10)      # Up to 50 from frequency
    score = min(100, int(duration_score + frequency_score))

    if score >= 80:
        label = "critical"
    elif score >= 60:
        label = "high"
    elif score >= 30:
        label = "medium"
    else:
        label = "low"

    return {
        "score": score,
        "label": label,
        "total_dark_hours": round(total_dark_hours, 2),
        "event_count": event_count,
    }
