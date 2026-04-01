"""NATO interoperability export endpoints (GAP-04).

Provides CoT and STANAG 5527/NFFI XML export for NATO C2 integration.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from app.modules.interop.cot_serializer import (
    alert_to_cot,
    vessel_position_to_cot,
)
from app.modules.interop.stanag5527_serializer import (
    alert_to_nffi,
    batch_tracks_to_nffi,
    vessel_to_nffi,
)

_log = logging.getLogger("aegisais.interop")

router = APIRouter()


@router.get("/cot/vessel/{mmsi}", response_class=Response)
async def export_vessel_cot(
    mmsi: str,
    lat: float = Query(...),
    lon: float = Query(...),
    sog: float | None = Query(None),
    cog: float | None = Query(None),
    heading: float | None = Query(None),
    vessel_name: str | None = Query(None),
):
    """Export a vessel position as Cursor-on-Target XML."""
    xml = vessel_position_to_cot(
        mmsi=mmsi, lat=lat, lon=lon, sog=sog, cog=cog,
        heading=heading, vessel_name=vessel_name,
    )
    return Response(content=xml, media_type="application/xml")


@router.get("/cot/alert/{alert_id}", response_class=Response)
async def export_alert_cot(
    alert_id: int,
    alert_type: str = Query(...),
    severity: int = Query(...),
    mmsi: str = Query(...),
    lat: float = Query(...),
    lon: float = Query(...),
    summary: str = Query(""),
):
    """Export an alert as Cursor-on-Target XML."""
    xml = alert_to_cot(
        alert_id=alert_id, alert_type=alert_type, severity=severity,
        mmsi=mmsi, lat=lat, lon=lon, summary=summary,
    )
    return Response(content=xml, media_type="application/xml")


@router.get("/nffi/vessel/{mmsi}", response_class=Response)
async def export_vessel_nffi(
    mmsi: str,
    lat: float = Query(...),
    lon: float = Query(...),
    sog: float | None = Query(None),
    cog: float | None = Query(None),
    heading: float | None = Query(None),
    vessel_name: str | None = Query(None),
    imo: str | None = Query(None),
    flag_state: str | None = Query(None),
):
    """Export a vessel position as STANAG 5527/NFFI XML."""
    xml = vessel_to_nffi(
        mmsi=mmsi, lat=lat, lon=lon, sog=sog, cog=cog,
        heading=heading, vessel_name=vessel_name, imo=imo,
        flag_state=flag_state,
    )
    return Response(content=xml, media_type="application/xml")


@router.get("/nffi/alert/{alert_id}", response_class=Response)
async def export_alert_nffi(
    alert_id: int,
    alert_type: str = Query(...),
    severity: int = Query(...),
    mmsi: str = Query(...),
    lat: float = Query(...),
    lon: float = Query(...),
    summary: str = Query(""),
):
    """Export an alert as STANAG 5527/NFFI XML."""
    xml = alert_to_nffi(
        alert_id=alert_id, alert_type=alert_type, severity=severity,
        mmsi=mmsi, lat=lat, lon=lon, summary=summary,
    )
    return Response(content=xml, media_type="application/xml")
