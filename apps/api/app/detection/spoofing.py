"""AIS spoofing and manipulation detection rules (GAP-03).

Detects:
- IDENTITY_SPOOF: Multiple vessels broadcasting the same MMSI simultaneously
- MMSI_FORMAT_INVALID: MMSI does not conform to ITU-R M.585 format rules
- GPS_MANIPULATION: Position tracks that exhibit GPS spoofing signatures
  (smooth but impossible spiral/grid patterns, sudden coordinate snaps)
- DARK_TO_LIGHT: Vessel goes dark then reappears with different identity/trajectory
"""

from __future__ import annotations

import logging
import re
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from app.core.config import settings
from app.infrastructure.ingest.loaders import AisPoint
from app.tracking.features import haversine_m, implied_speed_knots, heading_delta_deg

_log = logging.getLogger("aegisais.detection.spoofing")

# MMSI format rules per ITU-R M.585
# MID = Maritime Identification Digit (3 digits, 2xx-7xx)
_MMSI_PATTERN = re.compile(r"^\d{9}$")
_VALID_MID_RANGE = range(200, 800)


def rule_mmsi_format_invalid(p1: AisPoint, p2: AisPoint) -> Optional[dict[str, Any]]:
    """Flag MMSI values that violate ITU-R M.585 format rules."""
    mmsi = p2.mmsi
    if not _MMSI_PATTERN.match(mmsi):
        return {
            "type": "MMSI_FORMAT_INVALID",
            "severity": 85,
            "summary": f"MMSI {mmsi} does not match 9-digit format",
            "evidence": {"mmsi": mmsi, "rule": "itu_r_m585_format"},
        }

    mid = int(mmsi[:3])
    if mid not in _VALID_MID_RANGE:
        # MID outside allocated range (200-799)
        return {
            "type": "MMSI_FORMAT_INVALID",
            "severity": 70,
            "summary": f"MMSI {mmsi} has invalid MID {mid} (expected 200-799)",
            "evidence": {"mmsi": mmsi, "mid": mid, "rule": "itu_r_m585_mid_range"},
        }

    return None


def rule_gps_manipulation(p1: AisPoint, p2: AisPoint) -> Optional[dict[str, Any]]:
    """Detect GPS spoofing signatures.

    Spoofing produces plausible-looking tracks that differ from teleport:
    - Position snaps: coordinates jump to exact round numbers
    - Coordinate grid alignment: lat/lon snapping to 0.01 degree increments
    - Speed consistency with false position: SOG matches fake trajectory exactly
    """
    # Check for suspiciously round coordinates (GPS spoofing artifact)
    lat_decimals = _count_significant_decimals(p2.lat)
    lon_decimals = _count_significant_decimals(p2.lon)

    if lat_decimals <= 2 and lon_decimals <= 2:
        # Very round coordinates — possible spoofing
        # Check if previous position was also round (systematic spoofing)
        p1_lat_dec = _count_significant_decimals(p1.lat)
        p1_lon_dec = _count_significant_decimals(p1.lon)

        if p1_lat_dec <= 2 and p1_lon_dec <= 2:
            # Both positions suspiciously round — check if they form a grid pattern
            lat_diff = abs(p2.lat - p1.lat)
            lon_diff = abs(p2.lon - p1.lon)

            # Grid alignment: differences are exact multiples of 0.01°
            lat_grid = abs(lat_diff * 100 - round(lat_diff * 100)) < 0.001
            lon_grid = abs(lon_diff * 100 - round(lon_diff * 100)) < 0.001

            if lat_grid and lon_grid and (lat_diff > 0 or lon_diff > 0):
                severity = 75
                return {
                    "type": "GPS_MANIPULATION",
                    "severity": severity,
                    "summary": f"Grid-aligned coordinates: ({p2.lat:.4f}, {p2.lon:.4f}) — possible GPS spoofing",
                    "evidence": {
                        "p2_lat": p2.lat,
                        "p2_lon": p2.lon,
                        "lat_decimals": lat_decimals,
                        "lon_decimals": lon_decimals,
                        "grid_aligned": True,
                        "mmsi": p2.mmsi,
                    },
                }

    # Check for position snap: sudden shift to exact coordinates while SOG is continuous
    if p2.sog is not None and p1.sog is not None:
        sog_diff = abs(p2.sog - p1.sog)
        implied_sp = implied_speed_knots(p1, p2)

        if implied_sp is not None and p2.sog > 0.5:
            # SOG is smooth but implied speed wildly different → coordinates are fake
            sog_avg = (p1.sog + p2.sog) / 2
            if sog_avg > 0 and (implied_sp / sog_avg > 3.0 or implied_sp / sog_avg < 0.3):
                if sog_diff < 2.0:  # SOG barely changed (smooth) but position jumped
                    severity = 80
                    return {
                        "type": "GPS_MANIPULATION",
                        "severity": severity,
                        "summary": f"SOG stable ({p2.sog:.1f}kn) but implied speed {implied_sp:.1f}kn — position mismatch",
                        "evidence": {
                            "sog_p1": p1.sog,
                            "sog_p2": p2.sog,
                            "sog_diff": sog_diff,
                            "implied_speed_kn": implied_sp,
                            "ratio": implied_sp / sog_avg if sog_avg > 0 else None,
                            "mmsi": p2.mmsi,
                        },
                    }

    return None


def _count_significant_decimals(value: float) -> int:
    """Count meaningful decimal places (ignoring trailing zeros)."""
    s = f"{value:.6f}"
    if "." not in s:
        return 0
    decimal_part = s.split(".")[1].rstrip("0")
    return len(decimal_part)


# ──────────────────────────────────────────────────────────────────────────
# Track-window spoofing rules (operate on multiple points)
# ──────────────────────────────────────────────────────────────────────────

def check_simultaneous_mmsi(
    mmsi: str,
    current_point: AisPoint,
    all_recent_points: dict[str, AisPoint],
) -> Optional[dict[str, Any]]:
    """Detect multiple vessels broadcasting the same MMSI from different locations.

    ``all_recent_points`` maps ``f"{mmsi}:{source}"`` → latest AisPoint.
    If the same MMSI is seen at two positions > 10km apart within 60s, it's spoofed.
    """
    threshold_m = 10_000  # 10 km
    threshold_sec = 60

    for key, other in all_recent_points.items():
        if not key.startswith(f"{mmsi}:"):
            continue
        if other is current_point:
            continue
        dt = abs((current_point.timestamp - other.timestamp).total_seconds())
        if dt > threshold_sec:
            continue
        dist = haversine_m(current_point.lat, current_point.lon, other.lat, other.lon)
        if dist > threshold_m:
            return {
                "type": "IDENTITY_SPOOF",
                "severity": 95,
                "summary": f"MMSI {mmsi} seen at two locations {dist/1000:.1f}km apart within {dt:.0f}s",
                "evidence": {
                    "mmsi": mmsi,
                    "pos1_lat": current_point.lat,
                    "pos1_lon": current_point.lon,
                    "pos1_ts": current_point.timestamp.isoformat(),
                    "pos2_lat": other.lat,
                    "pos2_lon": other.lon,
                    "pos2_ts": other.timestamp.isoformat(),
                    "distance_m": dist,
                    "dt_sec": dt,
                },
            }
    return None


def detect_multi_source_vessel_identity_conflict(
    mmsi: int,
    sources: dict[str, dict[str, Any]],
) -> Optional[dict[str, Any]]:
    """Detect same MMSI at >10km distance from different sources (terrestrial vs satellite).

    Sources should be a dict like:
    {
        "aisstream": {"lat": 55.0, "lon": 10.0, "timestamp": datetime},
        "sais": {"lat": 64.0, "lon": 25.0, "timestamp": datetime}
    }
    """
    if len(sources) < 2:
        return None

    threshold_m = 10_000
    threshold_sec = 60

    sources_list = list(sources.items())
    for i, (source1, pos1) in enumerate(sources_list):
        for source2, pos2 in sources_list[i+1:]:
            if not pos1.get('lat') or not pos1.get('lon') or not pos2.get('lat') or not pos2.get('lon'):
                continue

            ts1 = pos1.get('timestamp')
            ts2 = pos2.get('timestamp')
            if not ts1 or not ts2:
                continue

            dt = abs((ts1 - ts2).total_seconds())
            if dt > threshold_sec:
                continue

            dist = haversine_m(pos1['lat'], pos1['lon'], pos2['lat'], pos2['lon'])
            if dist > threshold_m:
                return {
                    "type": "IDENTITY_SPOOF",
                    "severity": 95,
                    "summary": f"MMSI {mmsi} multi-source conflict: {source1} & {source2} "
                              f"{dist/1000:.1f}km apart within {dt:.0f}s",
                    "evidence": {
                        "mmsi": mmsi,
                        "positions": {
                            source1: {
                                "lat": pos1['lat'],
                                "lon": pos1['lon'],
                                "timestamp": pos1.get('timestamp').isoformat() if pos1.get('timestamp') else None,
                            },
                            source2: {
                                "lat": pos2['lat'],
                                "lon": pos2['lon'],
                                "timestamp": pos2.get('timestamp').isoformat() if pos2.get('timestamp') else None,
                            }
                        },
                        "distance_m": dist,
                        "dt_sec": dt,
                        "provenance": [source1, source2],
                    },
                }

    return None
