"""GEBCO bathymetry service.

Provides water depth lookup for vessel position validation.
Uses GEBCO 2024 grid (if available locally) or the GEBCO Web Map Service
for on-demand depth queries.

Key detection: vessel reported in water shallower than its draft = anomaly.

GEBCO WMS: https://www.gebco.net/data_and_products/gebco_web_services/web_map_service/
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

_log = logging.getLogger("aegisais.bathymetry")

# Open Topo Data API (free, no key, uses GEBCO 2020 dataset)
_DEPTH_API_URL = "https://api.opentopodata.org/v1/gebco2020"

_client: Optional[httpx.AsyncClient] = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(20.0, connect=5.0),
        )
    return _client


async def get_depth_at_position(
    lat: float,
    lon: float,
) -> Optional[dict[str, Any]]:
    """Query water depth at a position using Open Topo Data (GEBCO 2020).

    Returns depth in meters (negative = below sea level) or None on failure.
    """
    try:
        client = _get_client()
        resp = await client.get(
            _DEPTH_API_URL,
            params={"locations": f"{lat},{lon}"},
        )
        resp.raise_for_status()

        data = resp.json()
        if data.get("status") != "OK" or not data.get("results"):
            return None

        elevation = data["results"][0].get("elevation")
        if elevation is None:
            return None

        return {
            "lat": lat,
            "lon": lon,
            "depth_m": elevation,
            "is_land": elevation > 0,
            "depth_category": _classify_depth(elevation),
        }
    except httpx.TimeoutException:
        _log.warning("Bathymetry timeout for (%.4f, %.4f)", lat, lon)
        return None
    except httpx.HTTPStatusError as e:
        _log.warning("Bathymetry error %d for (%.4f, %.4f)", e.response.status_code, lat, lon)
        return None
    except Exception as e:
        _log.warning("Bathymetry lookup failed: %s", e)
        return None


def _classify_depth(depth_m: float) -> str:
    """Classify water depth category."""
    if depth_m > 0:
        return "land"
    abs_depth = abs(depth_m)
    if abs_depth < 10:
        return "very_shallow"
    if abs_depth < 50:
        return "shallow"
    if abs_depth < 200:
        return "coastal"
    if abs_depth < 2000:
        return "continental_shelf"
    if abs_depth < 6000:
        return "deep_ocean"
    return "hadal"


def check_draft_depth_anomaly(
    depth_m: float,
    vessel_draft_m: Optional[float] = None,
    vessel_type: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    """Check if a vessel's reported position is impossible given water depth.

    If the water is shallower than the vessel's draft, the position is
    physically impossible — indicating spoofing or data error.
    """
    if depth_m > 0:
        # Vessel reported on land
        return {
            "type": "POSITION_ON_LAND",
            "severity": 90,
            "depth_m": depth_m,
            "summary": "Vessel reported at a position on land — likely GPS spoofing or data error",
        }

    abs_depth = abs(depth_m)

    # If known draft, check against depth
    if vessel_draft_m and abs_depth < vessel_draft_m:
        return {
            "type": "DRAFT_DEPTH_MISMATCH",
            "severity": 85,
            "depth_m": depth_m,
            "vessel_draft_m": vessel_draft_m,
            "summary": f"Water depth ({abs_depth:.1f}m) less than vessel draft ({vessel_draft_m:.1f}m) — position impossible",
        }

    # Heuristic: large vessels (tankers, container ships) can't operate in <5m
    minimum_depths = {
        "tanker": 8.0,
        "container": 10.0,
        "bulk_carrier": 8.0,
        "cruise": 6.0,
    }

    if vessel_type and vessel_type.lower() in minimum_depths:
        min_depth = minimum_depths[vessel_type.lower()]
        if abs_depth < min_depth:
            return {
                "type": "DEPTH_VESSEL_TYPE_MISMATCH",
                "severity": 75,
                "depth_m": depth_m,
                "vessel_type": vessel_type,
                "minimum_expected_depth_m": min_depth,
                "summary": f"Water depth ({abs_depth:.1f}m) too shallow for {vessel_type} (min {min_depth:.1f}m)",
            }

    return None
