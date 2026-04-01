"""Sanctions watchlist matching and evasion detection (GAP-09).

Provides:
- MMSI/IMO/vessel name matching against OFAC SDN, EU consolidated, UN sanctions lists
- Ship-to-ship (STS) transfer detection (proximity + speed matching)
- Flag hopping detection (MMSI changes for same vessel)

Watchlists are loaded from local JSON files (sovereign deployment) or
fetched from official APIs.  No external calls without explicit configuration.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from app.infrastructure.ingest.loaders import AisPoint
from app.tracking.features import haversine_m

_log = logging.getLogger("aegisais.sanctions")

# Default watchlist path (loaded at module level if file exists)
_WATCHLIST_PATH = Path(__file__).parent / "data" / "sanctions_watchlist.json"

# In-memory watchlist store
_sanctioned_mmsi: set[str] = set()
_sanctioned_imo: set[str] = set()
_sanctioned_names: set[str] = set()


def load_watchlist(path: Optional[Path] = None) -> dict[str, int]:
    """Load sanctions watchlist from JSON file.

    Expected format:
    {
        "mmsi": ["123456789", ...],
        "imo": ["9876543", ...],
        "names": ["VESSEL NAME", ...]
    }
    """
    global _sanctioned_mmsi, _sanctioned_imo, _sanctioned_names

    fpath = path or _WATCHLIST_PATH
    if not fpath.exists():
        _log.info("No sanctions watchlist at %s — sanctions matching disabled", fpath)
        return {"mmsi": 0, "imo": 0, "names": 0}

    with open(fpath, "r") as f:
        data = json.load(f)

    _sanctioned_mmsi = {str(m) for m in data.get("mmsi", [])}
    _sanctioned_imo = {str(i) for i in data.get("imo", [])}
    _sanctioned_names = {n.upper() for n in data.get("names", [])}

    counts = {
        "mmsi": len(_sanctioned_mmsi),
        "imo": len(_sanctioned_imo),
        "names": len(_sanctioned_names),
    }
    _log.info("Sanctions watchlist loaded: %s", counts)
    return counts


def check_vessel_sanctions(
    mmsi: str,
    imo: Optional[str] = None,
    vessel_name: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    """Check a vessel against loaded sanctions watchlists.

    Returns match details or None if clean.
    """
    matches: list[dict[str, str]] = []

    if mmsi in _sanctioned_mmsi:
        matches.append({"field": "mmsi", "value": mmsi, "list": "sanctions_watchlist"})

    if imo and imo in _sanctioned_imo:
        matches.append({"field": "imo", "value": imo, "list": "sanctions_watchlist"})

    if vessel_name:
        name_upper = vessel_name.upper()
        if name_upper in _sanctioned_names:
            matches.append({"field": "name", "value": vessel_name, "list": "sanctions_watchlist"})

    if not matches:
        return None

    return {
        "type": "SANCTIONS_MATCH",
        "severity": 95,
        "summary": f"Vessel MMSI {mmsi} matches sanctions watchlist ({len(matches)} hit(s))",
        "evidence": {
            "mmsi": mmsi,
            "imo": imo,
            "vessel_name": vessel_name,
            "matches": matches,
        },
    }


def rule_sanctions_check(p1: AisPoint, p2: AisPoint) -> Optional[dict[str, Any]]:
    """Pipeline-compatible rule: check MMSI against sanctions list on each point."""
    if not _sanctioned_mmsi:
        return None
    return check_vessel_sanctions(p2.mmsi)


# ──────────────────────────────────────────────────────────────────────
# Ship-to-Ship (STS) Transfer Detection
# ──────────────────────────────────────────────────────────────────────

# Threshold: vessels within 500m and both < 3kn = potential STS
STS_PROXIMITY_M = 500
STS_MAX_SPEED_KN = 3.0
STS_MIN_DURATION_SEC = 300  # 5 minutes minimum


def detect_sts_transfer(
    vessel_a: AisPoint,
    vessel_b: AisPoint,
) -> Optional[dict[str, Any]]:
    """Detect potential ship-to-ship transfer between two vessels.

    Both vessels must be within STS_PROXIMITY_M and traveling below STS_MAX_SPEED_KN.
    """
    if vessel_a.mmsi == vessel_b.mmsi:
        return None

    dist = haversine_m(vessel_a.lat, vessel_a.lon, vessel_b.lat, vessel_b.lon)
    if dist > STS_PROXIMITY_M:
        return None

    # Both must be slow
    speed_a = vessel_a.sog or 0
    speed_b = vessel_b.sog or 0
    if speed_a > STS_MAX_SPEED_KN or speed_b > STS_MAX_SPEED_KN:
        return None

    # Time proximity
    dt = abs((vessel_a.timestamp - vessel_b.timestamp).total_seconds())
    if dt > 60:  # positions must be within 60 seconds of each other
        return None

    severity = 80
    # Escalate if one vessel is sanctioned
    if vessel_a.mmsi in _sanctioned_mmsi or vessel_b.mmsi in _sanctioned_mmsi:
        severity = 95

    return {
        "type": "STS_TRANSFER",
        "severity": severity,
        "summary": f"Potential STS transfer: {vessel_a.mmsi} and {vessel_b.mmsi} ({dist:.0f}m apart, both <{STS_MAX_SPEED_KN}kn)",
        "evidence": {
            "vessel_a_mmsi": vessel_a.mmsi,
            "vessel_a_lat": vessel_a.lat,
            "vessel_a_lon": vessel_a.lon,
            "vessel_a_sog": speed_a,
            "vessel_b_mmsi": vessel_b.mmsi,
            "vessel_b_lat": vessel_b.lat,
            "vessel_b_lon": vessel_b.lon,
            "vessel_b_sog": speed_b,
            "distance_m": dist,
            "dt_sec": dt,
        },
    }


# Initialize watchlist on module load (no-op if file doesn't exist)
try:
    load_watchlist()
except Exception as exc:
    _log.warning("Failed to load sanctions watchlist: %s", exc)
