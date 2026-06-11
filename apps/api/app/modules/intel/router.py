"""Intelligence product endpoints (GAP-11)."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Query

from app.modules.intel.service import (
    generate_area_sitrep,
    generate_intsum,
    generate_vessel_dossier,
)

_log = logging.getLogger("aegisais.intel.api")

router = APIRouter()


@router.get("/intsum")
async def get_intsum(
    area: str = Query("Baltic Sea"),
    hours: int = Query(24, ge=1, le=720),
):
    """Generate an Intelligence Summary for the specified period."""
    now = datetime.now(timezone.utc)
    period_start = now - timedelta(hours=hours)

    # In production, this would query the alerts DB.
    # For now, return the INTSUM template structure.
    return await generate_intsum(
        alerts=[],
        period_start=period_start,
        period_end=now,
        area_name=area,
    )


@router.get("/dossier/{mmsi}")
async def get_vessel_dossier(mmsi: str):
    """Generate a complete vessel dossier."""
    return await generate_vessel_dossier(mmsi=mmsi)


@router.get("/sitrep")
async def get_area_sitrep(
    area: str = Query("Baltic Sea"),
    hours: int = Query(24, ge=1, le=720),
):
    """Generate an Area Situation Report."""
    return await generate_area_sitrep(
        area_name=area,
        alerts=[],
        vessel_count=0,
        period_hours=hours,
    )
