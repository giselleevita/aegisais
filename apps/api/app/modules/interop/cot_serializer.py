"""Cursor-on-Target (CoT) XML serializer (GAP-04).

Serializes AegisAIS alerts, tracks, and vessel entities into MIL-STD CoT XML
format for integration with TAK Server, ATAK, and NATO C2 systems.

CoT specification: MIL-STD-6040 / ATAK CoT Event Schema
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from xml.etree.ElementTree import Element, SubElement, tostring


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


# CoT type mappings for AIS vessel types
_VESSEL_COT_TYPE = "a-n-S-C-m"  # atom - neutral - Surface - Craft - maritime
_ALERT_COT_TYPE = "b-m-r"        # bit - maritime - report


def vessel_position_to_cot(
    mmsi: str,
    lat: float,
    lon: float,
    sog: Optional[float] = None,
    cog: Optional[float] = None,
    heading: Optional[float] = None,
    vessel_name: Optional[str] = None,
    timestamp: Optional[datetime] = None,
    stale_minutes: int = 10,
) -> str:
    """Serialize a vessel position into CoT XML.

    Returns a complete CoT event XML string suitable for TAK Server ingestion.
    """
    now = timestamp or _utcnow()
    stale = now + timedelta(minutes=stale_minutes)
    uid = f"aegisais.vessel.{mmsi}"

    event = Element("event")
    event.set("version", "2.0")
    event.set("uid", uid)
    event.set("type", _VESSEL_COT_TYPE)
    event.set("time", _iso(now))
    event.set("start", _iso(now))
    event.set("stale", _iso(stale))
    event.set("how", "m-g")  # machine-generated

    point = SubElement(event, "point")
    point.set("lat", f"{lat:.6f}")
    point.set("lon", f"{lon:.6f}")
    point.set("hae", "0")  # height above ellipsoid (sea level)
    point.set("ce", "10")  # circular error (meters)
    point.set("le", "0")   # linear error

    detail = SubElement(event, "detail")

    # Contact info
    contact = SubElement(detail, "contact")
    contact.set("callsign", vessel_name or f"MMSI-{mmsi}")

    # Track info (speed, course)
    if sog is not None or cog is not None:
        track_el = SubElement(detail, "track")
        if sog is not None:
            track_el.set("speed", f"{sog * 0.514444:.2f}")  # knots to m/s
        if cog is not None:
            track_el.set("course", f"{cog:.1f}")

    # Remarks with AIS metadata
    remarks = SubElement(detail, "remarks")
    parts = [f"MMSI:{mmsi}"]
    if heading is not None and heading != 511:
        parts.append(f"HDG:{heading:.0f}")
    if sog is not None:
        parts.append(f"SOG:{sog:.1f}kn")
    remarks.text = " ".join(parts)

    # AegisAIS provenance
    _add_provenance(detail, "vessel_position")

    return tostring(event, encoding="unicode", xml_declaration=False)


def alert_to_cot(
    alert_id: str | int,
    alert_type: str,
    severity: int,
    mmsi: str,
    lat: float,
    lon: float,
    summary: str,
    timestamp: Optional[datetime] = None,
    stale_minutes: int = 30,
) -> str:
    """Serialize an AegisAIS alert into CoT XML."""
    now = timestamp or _utcnow()
    stale = now + timedelta(minutes=stale_minutes)
    uid = f"aegisais.alert.{alert_id}"

    event = Element("event")
    event.set("version", "2.0")
    event.set("uid", uid)
    event.set("type", _ALERT_COT_TYPE)
    event.set("time", _iso(now))
    event.set("start", _iso(now))
    event.set("stale", _iso(stale))
    event.set("how", "m-g")

    point = SubElement(event, "point")
    point.set("lat", f"{lat:.6f}")
    point.set("lon", f"{lon:.6f}")
    point.set("hae", "0")
    point.set("ce", "100")
    point.set("le", "0")

    detail = SubElement(event, "detail")

    contact = SubElement(detail, "contact")
    contact.set("callsign", f"ALERT-{alert_type}-{mmsi}")

    remarks = SubElement(detail, "remarks")
    remarks.text = f"[{alert_type}] Severity:{severity}/100 MMSI:{mmsi} — {summary}"

    # Alert-specific metadata
    alert_meta = SubElement(detail, "_aegisais_alert")
    alert_meta.set("alert_type", alert_type)
    alert_meta.set("severity", str(severity))
    alert_meta.set("mmsi", mmsi)
    alert_meta.set("alert_id", str(alert_id))

    _add_provenance(detail, "alert")

    return tostring(event, encoding="unicode", xml_declaration=False)


def track_to_cot_events(
    mmsi: str,
    positions: list[dict[str, Any]],
    vessel_name: Optional[str] = None,
) -> list[str]:
    """Convert a vessel track (list of positions) into a sequence of CoT events."""
    events = []
    for pos in positions:
        try:
            ts = pos.get("timestamp")
            if isinstance(ts, str):
                ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            events.append(vessel_position_to_cot(
                mmsi=mmsi,
                lat=pos["lat"],
                lon=pos["lon"],
                sog=pos.get("sog"),
                cog=pos.get("cog"),
                heading=pos.get("heading"),
                vessel_name=vessel_name,
                timestamp=ts,
            ))
        except (KeyError, ValueError):
            continue
    return events


def _add_provenance(detail: Element, data_type: str) -> None:
    """Add AegisAIS provenance metadata to CoT detail element."""
    prov = SubElement(detail, "_aegisais_provenance")
    prov.set("system", "AegisAIS")
    prov.set("version", "0.1.0")
    prov.set("data_type", data_type)
    prov.set("generated_at", _iso(_utcnow()))
