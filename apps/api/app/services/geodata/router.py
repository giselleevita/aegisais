"""Geodata and environmental context API endpoints."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Query

from app.services.geodata.eez import get_eez_zones, identify_eez, check_flag_eez_mismatch
from app.services.weather import get_marine_weather, is_weather_relevant_for_anomaly
from app.services.bathymetry import get_depth_at_position, check_draft_depth_anomaly

_log = logging.getLogger("aegisais.geodata.api")

router = APIRouter()


@router.get("/eez/identify")
async def identify_eez_for_position(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
):
    """Identify which Exclusive Economic Zone a position falls within."""
    result = identify_eez(lon, lat)
    return {
        "lat": lat,
        "lon": lon,
        "eez": result,
        "international_waters": result is None,
    }


@router.get("/eez/zones")
async def list_eez_zones():
    """List all loaded EEZ boundary zones."""
    zones = get_eez_zones()
    return {
        "count": len(zones),
        "zones": [
            {
                "name": z["name"],
                "sovereign": z["sovereign"],
                "iso3": z["iso3"],
                "mrgid": z.get("mrgid"),
                "bbox": z.get("bbox"),
            }
            for z in zones
        ],
    }


@router.get("/eez/flag-check")
async def check_flag_eez(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    flag_iso3: str = Query(..., min_length=3, max_length=3),
):
    """Check if a vessel's flag state matches the EEZ it is operating in."""
    result = check_flag_eez_mismatch(lon, lat, flag_iso3)
    return {
        "lat": lat,
        "lon": lon,
        "flag_iso3": flag_iso3,
        "mismatch": result is not None,
        "details": result,
    }


@router.get("/weather")
async def get_weather_at_position(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    vessel_sog: Optional[float] = Query(None, ge=0),
):
    """Get marine weather conditions at a position."""
    weather = await get_marine_weather(lat, lon)
    if weather is None:
        return {"lat": lat, "lon": lon, "available": False, "weather": None}

    anomaly_context = None
    if vessel_sog is not None:
        anomaly_context = is_weather_relevant_for_anomaly(weather, vessel_sog)

    return {
        "lat": lat,
        "lon": lon,
        "available": True,
        "weather": weather,
        "anomaly_context": anomaly_context,
    }


@router.get("/bathymetry")
async def get_depth(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    vessel_draft_m: Optional[float] = Query(None, ge=0),
    vessel_type: Optional[str] = Query(None),
):
    """Get water depth and draft validation at a position."""
    depth_data = await get_depth_at_position(lat, lon)
    if depth_data is None:
        return {"lat": lat, "lon": lon, "available": False, "depth": None}

    anomaly = None
    if depth_data.get("depth_m") is not None:
        anomaly = check_draft_depth_anomaly(
            depth_data["depth_m"],
            vessel_draft_m=vessel_draft_m,
            vessel_type=vessel_type,
        )

    return {
        "lat": lat,
        "lon": lon,
        "available": True,
        "depth": depth_data,
        "anomaly": anomaly,
    }


@router.get("/context")
async def get_full_environmental_context(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    vessel_sog: Optional[float] = Query(None, ge=0),
    vessel_draft_m: Optional[float] = Query(None, ge=0),
    vessel_type: Optional[str] = Query(None),
    flag_iso3: Optional[str] = Query(None, min_length=3, max_length=3),
):
    """Get complete environmental context for a vessel at position.

    Combines EEZ, weather, and bathymetry in a single call — ideal for
    enriching anomaly assessments.
    """
    eez = identify_eez(lon, lat)
    weather = await get_marine_weather(lat, lon)
    depth_data = await get_depth_at_position(lat, lon)

    flag_mismatch = None
    if flag_iso3:
        flag_mismatch = check_flag_eez_mismatch(lon, lat, flag_iso3)

    weather_context = None
    if weather and vessel_sog is not None:
        weather_context = is_weather_relevant_for_anomaly(weather, vessel_sog)

    depth_anomaly = None
    if depth_data and depth_data.get("depth_m") is not None:
        depth_anomaly = check_draft_depth_anomaly(
            depth_data["depth_m"],
            vessel_draft_m=vessel_draft_m,
            vessel_type=vessel_type,
        )

    return {
        "position": {"lat": lat, "lon": lon},
        "eez": eez,
        "international_waters": eez is None,
        "flag_mismatch": flag_mismatch,
        "weather": weather,
        "weather_anomaly_context": weather_context,
        "depth": depth_data,
        "depth_anomaly": depth_anomaly,
    }
