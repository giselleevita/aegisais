"""NATO interoperability export endpoints (GAP-04).

Provides CoT and STANAG 5527/NFFI XML export for NATO C2 integration.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from app.modules.alerts.schemas import AlertOut
from app.modules.alerts.service import AlertServiceDep
from app.modules.auth.dependencies import require_viewer_or_above
from app.modules.auth.models import User
from app.modules.interop.cot_serializer import (
    alert_to_cot,
    vessel_position_to_cot,
)
from app.modules.interop.stanag5527_serializer import (
    alert_to_nffi,
    vessel_to_nffi,
)
from app.modules.vessels.schemas import VesselLatestOut
from app.modules.vessels.service import VesselServiceDep

_log = logging.getLogger("aegisais.interop")

router = APIRouter()


def _coerce_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _extract_alert_coordinates(alert: AlertOut) -> tuple[float, float]:
    evidence = alert.evidence if isinstance(alert.evidence, dict) else {}

    coordinate_candidates = [
        (evidence.get("lat"), evidence.get("lon")),
        (evidence.get("latitude"), evidence.get("longitude")),
        (evidence.get("p2_lat"), evidence.get("p2_lon")),
        (evidence.get("position_lat"), evidence.get("position_lon")),
    ]

    current_position = evidence.get("current_position")
    if isinstance(current_position, dict):
        coordinate_candidates.append(
            (current_position.get("lat") or current_position.get("latitude"),
             current_position.get("lon") or current_position.get("longitude"))
        )

    for lat_raw, lon_raw in coordinate_candidates:
        lat = _coerce_float(lat_raw)
        lon = _coerce_float(lon_raw)
        if lat is not None and lon is not None:
            return lat, lon

    raise HTTPException(
        status_code=422,
        detail="Alert evidence does not contain exportable coordinates",
    )


def _extract_alert_summary(alert: AlertOut) -> str:
    if alert.summary:
        return alert.summary
    evidence = alert.evidence if isinstance(alert.evidence, dict) else {}
    return str(evidence.get("summary") or evidence.get("reason") or alert.type)


def _vessel_to_cot_xml(vessel: VesselLatestOut) -> str:
    return vessel_position_to_cot(
        mmsi=vessel.mmsi,
        lat=vessel.lat,
        lon=vessel.lon,
        sog=vessel.sog,
        cog=vessel.cog,
        heading=vessel.heading,
        timestamp=vessel.timestamp,
    )


def _vessel_to_nffi_xml(vessel: VesselLatestOut) -> str:
    return vessel_to_nffi(
        mmsi=vessel.mmsi,
        lat=vessel.lat,
        lon=vessel.lon,
        sog=vessel.sog,
        cog=vessel.cog,
        heading=vessel.heading,
        timestamp=vessel.timestamp,
    )


def _alert_to_cot_xml(alert: AlertOut) -> str:
    lat, lon = _extract_alert_coordinates(alert)
    return alert_to_cot(
        alert_id=alert.id,
        alert_type=alert.type,
        severity=alert.severity,
        mmsi=alert.mmsi,
        lat=lat,
        lon=lon,
        summary=_extract_alert_summary(alert),
        timestamp=alert.timestamp,
    )


def _alert_to_nffi_xml(alert: AlertOut) -> str:
    lat, lon = _extract_alert_coordinates(alert)
    return alert_to_nffi(
        alert_id=alert.id,
        alert_type=alert.type,
        severity=alert.severity,
        mmsi=alert.mmsi,
        lat=lat,
        lon=lon,
        summary=_extract_alert_summary(alert),
        timestamp=alert.timestamp,
    )


@router.get("/cot/vessel/{mmsi}", response_class=Response)
async def export_vessel_cot(
    mmsi: str,
    svc: VesselServiceDep,
    viewer: User = Depends(require_viewer_or_above),
):
    """Export a vessel position as Cursor-on-Target XML."""
    vessel = svc.get_vessel(mmsi, scope_user=viewer)
    xml = _vessel_to_cot_xml(vessel)
    return Response(content=xml, media_type="application/xml")


@router.get("/cot/alert/{alert_id}", response_class=Response)
async def export_alert_cot(
    alert_id: int,
    svc: AlertServiceDep,
    viewer: User = Depends(require_viewer_or_above),
):
    """Export an alert as Cursor-on-Target XML."""
    alert = svc.get_alert(alert_id, user=viewer)
    xml = _alert_to_cot_xml(alert)
    return Response(content=xml, media_type="application/xml")


@router.get("/nffi/vessel/{mmsi}", response_class=Response)
async def export_vessel_nffi(
    mmsi: str,
    svc: VesselServiceDep,
    viewer: User = Depends(require_viewer_or_above),
):
    """Export a vessel position as STANAG 5527/NFFI XML."""
    vessel = svc.get_vessel(mmsi, scope_user=viewer)
    xml = _vessel_to_nffi_xml(vessel)
    return Response(content=xml, media_type="application/xml")


@router.get("/nffi/alert/{alert_id}", response_class=Response)
async def export_alert_nffi(
    alert_id: int,
    svc: AlertServiceDep,
    viewer: User = Depends(require_viewer_or_above),
):
    """Export an alert as STANAG 5527/NFFI XML."""
    alert = svc.get_alert(alert_id, user=viewer)
    xml = _alert_to_nffi_xml(alert)
    return Response(content=xml, media_type="application/xml")
