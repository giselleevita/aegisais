"""
ITDAE detection rules.

Mirrors backend.app.detection.rules style — each rule is a function that returns
an AlertResult dict (type, severity, summary, evidence) or None.

Rules in this module are ITDAE-specific — they combine trajectory features
(from features_itdae.py) with geofence zone context to produce infrastructure
threat alerts.

Rule hierarchy (by severity):
  Tier 1 (high confidence):
    GEOFENCE_ENTRY       — vessel enters a critical/high cable zone
    LOITER_IN_ZONE       — vessel loitering inside a cable zone
    AIS_DARK_IN_ZONE     — vessel loses AIS inside cable zone then reappears

  Tier 2 (suspicious / lower confidence):
    SLOW_TRANSIT_ZONE    — unusually slow transit through cable zone
    REPEATED_GEOFENCE    — vessel makes multiple zone entries in short time
"""

import logging
from typing import Optional, Any

from app.modules.itdae.tracking.features_itdae import (
    TrajectoryFeatures,
    ItdaePoint,
    is_loitering,
    compute_trajectory_features,
    LOITER_MIN_DURATION_S,
    SLOW_TRANSIT_MAX_KN,
)
from app.modules.itdae.geofences.checker import get_zone_for_position

log = logging.getLogger("aegisais.itdae.detection")


# ── Severity constants ────────────────────────────────────────────────────────

_RISK_SEVERITY = {
    "critical": 90,
    "high":     70,
    "medium":   45,
}

# AIS nav statuses that are suspicious when in a cable zone:
#   0 = Under way using engine, 3 = Restricted manoeuvrability
_SUSPICIOUS_NAV_STATUS = {0, 3, 8}  # 8 = Engaged in fishing

# Dark gap thresholds
DARK_MIN_GAP_SEC    = 1800   # 30 min silence = suspicious
DARK_SEVERE_GAP_SEC = 7200   # 2 hr silence inside zone = critical


# ── Helper ───────────────────────────────────────────────────────────────────

def _zone_context(zone: dict) -> dict:
    return {
        "zone_id": zone["id"],
        "zone_name": zone["name"],
        "zone_risk_level": zone["risk_level"],
    }


# ── Tier 1 Rules ─────────────────────────────────────────────────────────────

def rule_geofence_entry(
    p1: ItdaePoint, p2: ItdaePoint
) ->Optional[ dict[str, Any]]:
    """
    Fires when a vessel transitions from outside a cable zone into one.

    Severity is driven by the zone's risk_level.
    Only fires on the crossing event (p1 outside, p2 inside).
    """
    zone_before = get_zone_for_position(lon=p1.lon, lat=p1.lat)
    zone_after  = get_zone_for_position(lon=p2.lon, lat=p2.lat)

    # Must have crossed INTO a zone this step
    if zone_after is None:
        return None
    if zone_before is not None and zone_before["id"] == zone_after["id"]:
        return None  # Already inside — not a new entry

    severity = _RISK_SEVERITY.get(zone_after["risk_level"], 50)
    dt = (p2.timestamp - p1.timestamp).total_seconds()
    implied_kn = compute_trajectory_features(p1, p2, [p1, p2]).implied_speed_kn

    log.info(
        "GEOFENCE_ENTRY: mmsi=%s entered zone=%s (risk=%s) speed=%.1f kn",
        p2.mmsi, zone_after["id"], zone_after["risk_level"], implied_kn,
    )
    return {
        "type": "GEOFENCE_ENTRY",
        "severity": severity,
        "summary": (
            f"Vessel entered cable zone '{zone_after['name']}' "
            f"(risk: {zone_after['risk_level']}) at {implied_kn:.1f} kn"
        ),
        "evidence": {
            "mmsi": p2.mmsi,
            "timestamp": p2.timestamp.isoformat(),
            "lat": p2.lat,
            "lon": p2.lon,
            "implied_speed_kn": implied_kn,
            "dt_sec": dt,
            **_zone_context(zone_after),
        },
    }


def rule_loiter_in_zone(
    window: list[ItdaePoint],
) ->Optional[ dict[str, Any]]:
    """
    Fires when a vessel has been loitering within a cable geofence zone.

    Requires the current end-of-window point to be inside a zone,
    and the loitering criterion to be met for the window.
    """
    if len(window) < 2:
        return None

    p_latest = window[-1]
    zone = get_zone_for_position(lon=p_latest.lon, lat=p_latest.lat)
    if zone is None:
        return None

    if not is_loitering(window):
        return None

    duration_min = (window[-1].timestamp - window[0].timestamp).total_seconds() / 60
    severity = _RISK_SEVERITY.get(zone["risk_level"], 50)
    # Escalate severity if loitering longer than 1 hour
    if duration_min >= 60:
        severity = min(100, severity + 10)

    log.info(
        "LOITER_IN_ZONE: mmsi=%s loitering in zone=%s for %.1f min",
        p_latest.mmsi, zone["id"], duration_min,
    )
    return {
        "type": "LOITER_IN_ZONE",
        "severity": severity,
        "summary": (
            f"Vessel loitering in cable zone '{zone['name']}' "
            f"for {duration_min:.0f} min (risk: {zone['risk_level']})"
        ),
        "evidence": {
            "mmsi": p_latest.mmsi,
            "duration_min": round(duration_min, 1),
            "window_size": len(window),
            "lat": p_latest.lat,
            "lon": p_latest.lon,
            **_zone_context(zone),
        },
    }


def rule_ais_dark_in_zone(
    p_before: ItdaePoint, p_after: ItdaePoint
) ->Optional[ dict[str, Any]]:
    """
    Fires when a vessel reappears after a long AIS silence, and either the
    disappearance or reappearance point is within a cable geofence zone.

    Dark gaps of 30–120 min are suspicious; >2 hr are critical.
    """
    dt = (p_after.timestamp - p_before.timestamp).total_seconds()
    if dt < DARK_MIN_GAP_SEC:
        return None

    zone_before = get_zone_for_position(lon=p_before.lon, lat=p_before.lat)
    zone_after  = get_zone_for_position(lon=p_after.lon, lat=p_after.lat)

    active_zone = zone_after or zone_before
    if active_zone is None:
        return None

    base_severity = _RISK_SEVERITY.get(active_zone["risk_level"], 50)
    if dt >= DARK_SEVERE_GAP_SEC:
        severity = min(100, base_severity + 10)
        label = f"{dt/3600:.1f} hr"
    else:
        severity = base_severity
        label = f"{dt/60:.0f} min"

    log.info(
        "AIS_DARK_IN_ZONE: mmsi=%s dark for %s near zone=%s",
        p_before.mmsi, label, active_zone["id"],
    )
    return {
        "type": "AIS_DARK_IN_ZONE",
        "severity": severity,
        "summary": (
            f"Vessel AIS dark for {label} near cable zone '{active_zone['name']}'"
        ),
        "evidence": {
            "mmsi": p_before.mmsi,
            "gap_sec": dt,
            "disappeared_at": p_before.timestamp.isoformat(),
            "reappeared_at": p_after.timestamp.isoformat(),
            "disappeared_lat": p_before.lat,
            "disappeared_lon": p_before.lon,
            "reappeared_lat": p_after.lat,
            "reappeared_lon": p_after.lon,
            "in_zone_before": zone_before is not None,
            "in_zone_after": zone_after is not None,
            **_zone_context(active_zone),
        },
    }


# ── Tier 2 Rules ─────────────────────────────────────────────────────────────

def rule_slow_transit_zone(
    p1: ItdaePoint, p2: ItdaePoint
) ->Optional[ dict[str, Any]]:
    """
    Tier-2: Vessel is moving very slowly (≤5 kn) through a cable zone but
    does not meet full loiter criteria. Still suspicious.
    """
    zone = get_zone_for_position(lon=p2.lon, lat=p2.lat)
    if zone is None:
        return None

    # Only use SOG if available, else skip
    sog = p2.speed
    if sog is None or sog > SLOW_TRANSIT_MAX_KN:
        return None
    if sog < 0.3:
        return None  # Anchored/moored — handled by LOITER rule

    base_severity = _RISK_SEVERITY.get(zone["risk_level"], 45) - 20  # lower than Tier 1
    severity = max(25, min(60, base_severity))

    log.info(
        "SLOW_TRANSIT_ZONE: mmsi=%s sog=%.1f kn in zone=%s (tier-2)",
        p2.mmsi, sog, zone["id"],
    )
    return {
        "type": "SLOW_TRANSIT_ZONE",
        "severity": severity,
        "summary": (
            f"Slow transit ({sog:.1f} kn) through cable zone '{zone['name']}' (Tier-2)"
        ),
        "evidence": {
            "mmsi": p2.mmsi,
            "sog_kn": sog,
            "lat": p2.lat,
            "lon": p2.lon,
            "timestamp": p2.timestamp.isoformat(),
            **_zone_context(zone),
        },
    }


# ── Rule registry ─────────────────────────────────────────────────────────────
#
# Used by pipeline_itdae.py to run all point-pair rules in one pass.
# Signature: (p1: ItdaePoint, p2: ItdaePoint) ->Optional[ AlertResult]
#
POINT_PAIR_RULES = [
    rule_geofence_entry,
    rule_slow_transit_zone,
    rule_ais_dark_in_zone,
]

# Window rules — called with the full track window list
# Signature: (window: list[ItdaePoint]) ->Optional[ AlertResult]
WINDOW_RULES = [
    rule_loiter_in_zone,
]
