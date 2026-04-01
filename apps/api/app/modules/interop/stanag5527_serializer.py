"""STANAG 5527 / NATO FFI (Force-Finding Information) XML serializer (GAP-04).

Serializes AegisAIS entities (vessels, alerts, tracks) into STANAG 5527
(NFFI — NATO Friendly Force Information) XML format for integration with
NATO C2 systems (ICC, BICES, TRITON).

Reference: STANAG 5527 Ed. 2 — NATO Force-Finding Information Format
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from xml.etree.ElementTree import Element, SubElement, tostring

_NFFI_NS = "urn:nato:stanag:5527:nffi:1:0"
_NFFI_PREFIX = "nffi"


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def vessel_to_nffi(
    mmsi: str,
    lat: float,
    lon: float,
    sog: Optional[float] = None,
    cog: Optional[float] = None,
    heading: Optional[float] = None,
    vessel_name: Optional[str] = None,
    imo: Optional[str] = None,
    flag_state: Optional[str] = None,
    vessel_type: Optional[str] = None,
    timestamp: Optional[datetime] = None,
) -> str:
    """Serialize a vessel position into STANAG 5527 NFFI XML."""
    now = timestamp or _utcnow()

    root = Element("NFCIMessage")
    root.set("xmlns", _NFFI_NS)
    root.set("schemaVersion", "1.0")

    header = SubElement(root, "MessageHeader")
    SubElement(header, "MessageID").text = f"aegisais-{mmsi}-{int(now.timestamp())}"
    SubElement(header, "SenderID").text = "AEGISAIS"
    SubElement(header, "DateTime").text = _iso(now)
    SubElement(header, "Classification").text = "UNCLASSIFIED"

    body = SubElement(root, "MessageBody")
    track = SubElement(body, "Track")

    # Track identity
    identity = SubElement(track, "TrackIdentity")
    SubElement(identity, "TrackNumber").text = f"T-{mmsi}"
    SubElement(identity, "TrackAffiliation").text = "UNKNOWN"
    SubElement(identity, "TrackEnvironment").text = "SURFACE"

    # Track identity amplification
    if vessel_name or imo or flag_state:
        amplification = SubElement(track, "TrackAmplification")
        if vessel_name:
            SubElement(amplification, "VesselName").text = vessel_name
        if imo:
            SubElement(amplification, "IMONumber").text = imo
        if flag_state:
            SubElement(amplification, "FlagState").text = flag_state
        SubElement(amplification, "MMSI").text = mmsi
        if vessel_type:
            SubElement(amplification, "VesselType").text = vessel_type

    # Position
    position = SubElement(track, "Position")
    SubElement(position, "Latitude").text = f"{lat:.6f}"
    SubElement(position, "Longitude").text = f"{lon:.6f}"
    SubElement(position, "PositionTime").text = _iso(now)
    SubElement(position, "PositionAccuracy").text = "10"  # meters

    # Kinematics
    if sog is not None or cog is not None or heading is not None:
        kinematics = SubElement(track, "Kinematics")
        if sog is not None:
            SubElement(kinematics, "Speed").text = f"{sog * 0.514444:.2f}"  # m/s
        if cog is not None:
            SubElement(kinematics, "Course").text = f"{cog:.1f}"
        if heading is not None and heading != 511:
            SubElement(kinematics, "Heading").text = f"{heading:.1f}"

    # Provenance
    provenance = SubElement(track, "DataSource")
    SubElement(provenance, "SourceSystem").text = "AEGISAIS"
    SubElement(provenance, "SourceType").text = "AIS"
    SubElement(provenance, "Confidence").text = "HIGH"

    return tostring(root, encoding="unicode", xml_declaration=True)


def alert_to_nffi(
    alert_id: str | int,
    alert_type: str,
    severity: int,
    mmsi: str,
    lat: float,
    lon: float,
    summary: str,
    timestamp: Optional[datetime] = None,
) -> str:
    """Serialize an AegisAIS alert into STANAG 5527 NFFI XML as a Track with alert annotation."""
    now = timestamp or _utcnow()

    root = Element("NFCIMessage")
    root.set("xmlns", _NFFI_NS)
    root.set("schemaVersion", "1.0")

    header = SubElement(root, "MessageHeader")
    SubElement(header, "MessageID").text = f"aegisais-alert-{alert_id}"
    SubElement(header, "SenderID").text = "AEGISAIS"
    SubElement(header, "DateTime").text = _iso(now)
    SubElement(header, "Classification").text = "UNCLASSIFIED"

    body = SubElement(root, "MessageBody")
    track = SubElement(body, "Track")

    identity = SubElement(track, "TrackIdentity")
    SubElement(identity, "TrackNumber").text = f"T-{mmsi}"
    SubElement(identity, "TrackAffiliation").text = "SUSPECT"
    SubElement(identity, "TrackEnvironment").text = "SURFACE"

    position = SubElement(track, "Position")
    SubElement(position, "Latitude").text = f"{lat:.6f}"
    SubElement(position, "Longitude").text = f"{lon:.6f}"
    SubElement(position, "PositionTime").text = _iso(now)

    # Alert annotation
    annotation = SubElement(track, "Annotation")
    SubElement(annotation, "AnnotationType").text = "ALERT"
    SubElement(annotation, "AnnotationText").text = f"[{alert_type}] Severity:{severity}/100 — {summary}"
    SubElement(annotation, "DateTime").text = _iso(now)

    alert_detail = SubElement(annotation, "AlertDetail")
    SubElement(alert_detail, "AlertType").text = alert_type
    SubElement(alert_detail, "Severity").text = str(severity)
    SubElement(alert_detail, "MMSI").text = mmsi
    SubElement(alert_detail, "AlertID").text = str(alert_id)

    provenance = SubElement(track, "DataSource")
    SubElement(provenance, "SourceSystem").text = "AEGISAIS"
    SubElement(provenance, "SourceType").text = "DETECTION"

    return tostring(root, encoding="unicode", xml_declaration=True)


def batch_tracks_to_nffi(
    tracks: list[dict[str, Any]],
) -> str:
    """Serialize multiple vessel tracks into a single NFFI message."""
    root = Element("NFCIMessage")
    root.set("xmlns", _NFFI_NS)
    root.set("schemaVersion", "1.0")

    header = SubElement(root, "MessageHeader")
    SubElement(header, "MessageID").text = f"aegisais-batch-{int(_utcnow().timestamp())}"
    SubElement(header, "SenderID").text = "AEGISAIS"
    SubElement(header, "DateTime").text = _iso(_utcnow())
    SubElement(header, "Classification").text = "UNCLASSIFIED"

    body = SubElement(root, "MessageBody")

    for t in tracks:
        track = SubElement(body, "Track")
        identity = SubElement(track, "TrackIdentity")
        SubElement(identity, "TrackNumber").text = f"T-{t['mmsi']}"
        SubElement(identity, "TrackAffiliation").text = "UNKNOWN"
        SubElement(identity, "TrackEnvironment").text = "SURFACE"

        position = SubElement(track, "Position")
        SubElement(position, "Latitude").text = f"{t['lat']:.6f}"
        SubElement(position, "Longitude").text = f"{t['lon']:.6f}"
        ts = t.get("timestamp")
        if isinstance(ts, str):
            SubElement(position, "PositionTime").text = ts
        elif isinstance(ts, datetime):
            SubElement(position, "PositionTime").text = _iso(ts)

        if t.get("sog") is not None or t.get("cog") is not None:
            kin = SubElement(track, "Kinematics")
            if t.get("sog") is not None:
                SubElement(kin, "Speed").text = f"{t['sog'] * 0.514444:.2f}"
            if t.get("cog") is not None:
                SubElement(kin, "Course").text = f"{t['cog']:.1f}"

    return tostring(root, encoding="unicode", xml_declaration=True)
