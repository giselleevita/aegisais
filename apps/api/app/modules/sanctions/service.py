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

from app.core.config import settings
from app.infrastructure.ingest.loaders import AisPoint
from app.tracking.features import haversine_m

_log = logging.getLogger("aegisais.sanctions")

# Default watchlist path (loaded at module level if file exists)
_WATCHLIST_PATH = Path(__file__).parent / "data" / "sanctions_watchlist.json"

# In-memory watchlist store
_sanctioned_mmsi: set[str] = set()
_sanctioned_imo: set[str] = set()
_sanctioned_names: set[str] = set()

FLAG_HOP_MAX_GAP_DAYS = 180
DARK_PORT_MIN_DURATION_SEC = 15 * 60
DARK_PORT_RADIUS_M = 25_000


def _resolve_watchlist_path(path: Optional[Path | str] = None) -> Path:
    if path is not None:
        return Path(path)

    configured = (settings.SANCTIONS_WATCHLIST_PATH or "").strip()
    if configured:
        return Path(configured)

    return _WATCHLIST_PATH


def _coerce_datetime(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        normalized = value.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    return None


def _normalize_identity_text(value: Optional[str]) -> str:
    if not value:
        return ""
    normalized = re.sub(r"[^A-Z0-9]+", " ", value.upper()).strip()
    return re.sub(r"\s+", " ", normalized)


def get_watchlist_status(path: Optional[Path | str] = None) -> dict[str, Any]:
    """Return operational metadata for the currently configured watchlist."""
    watchlist_path = _resolve_watchlist_path(path)
    status: dict[str, Any] = {
        "path": str(watchlist_path),
        "exists": watchlist_path.exists(),
        "mmsi_count": len(_sanctioned_mmsi),
        "imo_count": len(_sanctioned_imo),
        "name_count": len(_sanctioned_names),
        "source": "local file",
        "updated_at": None,
    }

    if not watchlist_path.exists():
        return status

    try:
        data = json.loads(watchlist_path.read_text())
    except (OSError, json.JSONDecodeError):
        return status

    status["source"] = data.get("_source", status["source"])
    status["updated_at"] = data.get("_updated_at")
    return status


def load_watchlist(path: Optional[Path | str] = None) -> dict[str, int]:
    """Load sanctions watchlist from JSON file.

    Expected format:
    {
        "mmsi": ["123456789", ...],
        "imo": ["9876543", ...],
        "names": ["VESSEL NAME", ...]
    }
    """
    global _sanctioned_mmsi, _sanctioned_imo, _sanctioned_names

    fpath = _resolve_watchlist_path(path)
    if not fpath.exists():
        _log.info("No sanctions watchlist at %s — sanctions matching disabled", fpath)
        _sanctioned_mmsi = set()
        _sanctioned_imo = set()
        _sanctioned_names = set()
        return {"mmsi": 0, "imo": 0, "names": 0}

    with open(fpath, "r", encoding="utf-8") as f:
        data = json.load(f)

    _sanctioned_mmsi = {str(m).strip() for m in data.get("mmsi", []) if str(m).strip()}
    _sanctioned_imo = {str(i).strip() for i in data.get("imo", []) if str(i).strip()}
    _sanctioned_names = {str(n).strip().upper() for n in data.get("names", []) if str(n).strip()}

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


def detect_flag_hopping(identity_snapshots: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
    """Detect suspicious vessel identity changes across historical observations.

    Requires either a stable IMO or a stable normalized vessel name to anchor
    the vessel identity, then looks for MMSI and flag-state changes over time.
    """
    if len(identity_snapshots) < 2:
        return None

    normalized_snapshots: list[dict[str, Any]] = []
    for snapshot in identity_snapshots:
        timestamp = _coerce_datetime(snapshot.get("timestamp"))
        if timestamp is None:
            continue

        normalized_snapshots.append(
            {
                "mmsi": str(snapshot.get("mmsi", "")).strip(),
                "imo": str(snapshot.get("imo", "")).strip(),
                "flag_state": _normalize_identity_text(snapshot.get("flag_state")),
                "vessel_name": _normalize_identity_text(snapshot.get("vessel_name")),
                "timestamp": timestamp,
            }
        )

    if len(normalized_snapshots) < 2:
        return None

    normalized_snapshots.sort(key=lambda item: item["timestamp"])
    first_seen = normalized_snapshots[0]["timestamp"]
    last_seen = normalized_snapshots[-1]["timestamp"]
    if (last_seen - first_seen) > timedelta(days=FLAG_HOP_MAX_GAP_DAYS):
        return None

    distinct_mmsi = {item["mmsi"] for item in normalized_snapshots if item["mmsi"]}
    distinct_flags = {item["flag_state"] for item in normalized_snapshots if item["flag_state"]}
    if len(distinct_mmsi) <= 1 and len(distinct_flags) <= 1:
        return None

    distinct_imo = {item["imo"] for item in normalized_snapshots if item["imo"]}
    distinct_names = {item["vessel_name"] for item in normalized_snapshots if item["vessel_name"]}
    if len(distinct_imo) > 1:
        return None
    if not distinct_imo and len(distinct_names) != 1:
        return None

    changes: list[dict[str, Any]] = []
    for previous, current in zip(normalized_snapshots, normalized_snapshots[1:]):
        changed_fields: list[str] = []
        if previous["mmsi"] and current["mmsi"] and previous["mmsi"] != current["mmsi"]:
            changed_fields.append("mmsi")
        if (
            previous["flag_state"]
            and current["flag_state"]
            and previous["flag_state"] != current["flag_state"]
        ):
            changed_fields.append("flag_state")

        if not changed_fields:
            continue

        changes.append(
            {
                "from": {
                    "mmsi": previous["mmsi"],
                    "flag_state": previous["flag_state"],
                    "timestamp": previous["timestamp"].isoformat(),
                },
                "to": {
                    "mmsi": current["mmsi"],
                    "flag_state": current["flag_state"],
                    "timestamp": current["timestamp"].isoformat(),
                },
                "changed_fields": changed_fields,
                "gap_hours": round(
                    (current["timestamp"] - previous["timestamp"]).total_seconds() / 3600,
                    2,
                ),
            }
        )

    if not changes:
        return None

    rapid_change = any(change["gap_hours"] <= 24 * 30 for change in changes)
    severity = 78 + min(9, len(changes) * 3)
    if len(distinct_mmsi) > 1 and len(distinct_flags) > 1:
        severity += 8
    if rapid_change:
        severity += 4
    severity = min(95, severity)

    anchor = next(iter(distinct_imo), None) or next(iter(distinct_names), None)
    anchor_kind = "imo" if distinct_imo else "vessel_name"

    return {
        "type": "FLAG_HOPPING",
        "severity": severity,
        "summary": (
            f"Potential flag hopping for {anchor_kind} {anchor}: "
            f"{len(distinct_mmsi)} MMSI(s), {len(distinct_flags)} flag state(s)"
        ),
        "evidence": {
            "anchor_kind": anchor_kind,
            "anchor": anchor,
            "first_seen": first_seen.isoformat(),
            "last_seen": last_seen.isoformat(),
            "distinct_mmsi": sorted(distinct_mmsi),
            "distinct_flags": sorted(distinct_flags),
            "changes": changes,
            "rapid_change": rapid_change,
        },
    }


def correlate_dark_activity_with_sanctioned_port(
    *,
    mmsi: str,
    dark_duration_sec: int,
    last_known_position: dict[str, Any],
    reappearance_position: dict[str, Any],
    sanctioned_ports: list[dict[str, Any]],
) -> Optional[dict[str, Any]]:
    """Correlate an AIS dark period with sanctioned-port proximity."""
    if dark_duration_sec < DARK_PORT_MIN_DURATION_SEC or not sanctioned_ports:
        return None

    def _match_port(position: dict[str, Any], stage: str) -> list[dict[str, Any]]:
        lat = position.get("lat")
        lon = position.get("lon")
        if lat is None or lon is None:
            return []

        matches: list[dict[str, Any]] = []
        for port in sanctioned_ports:
            port_lat = port.get("lat")
            port_lon = port.get("lon")
            if port_lat is None or port_lon is None:
                continue
            distance_m = haversine_m(float(lat), float(lon), float(port_lat), float(port_lon))
            if distance_m > DARK_PORT_RADIUS_M:
                continue
            matches.append(
                {
                    "stage": stage,
                    "port_name": port.get("name", "unknown"),
                    "country": port.get("country"),
                    "sanctions_regime": port.get("sanctions_regime"),
                    "distance_m": round(distance_m, 1),
                }
            )
        return matches

    matches = _match_port(last_known_position, "last_seen") + _match_port(
        reappearance_position,
        "reappeared",
    )
    if not matches:
        return None

    matched_stages = {match["stage"] for match in matches}
    matched_ports = sorted({match["port_name"] for match in matches})
    severity = 74
    if len(matched_stages) == 2:
        severity += 8
    if dark_duration_sec >= 2 * 60 * 60:
        severity += 8
    if len(matched_ports) > 1:
        severity += 4
    severity = min(95, severity)

    return {
        "type": "SANCTIONS_DARK_ACTIVITY",
        "severity": severity,
        "summary": (
            f"AIS dark activity for {mmsi} correlated with sanctioned port proximity: "
            f"{', '.join(matched_ports)}"
        ),
        "evidence": {
            "mmsi": mmsi,
            "dark_duration_sec": dark_duration_sec,
            "dark_hours": round(dark_duration_sec / 3600, 2),
            "matched_ports": matches,
            "last_known_position": last_known_position,
            "reappearance_position": reappearance_position,
            "radius_m": DARK_PORT_RADIUS_M,
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
