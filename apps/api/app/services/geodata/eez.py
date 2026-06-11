"""Exclusive Economic Zone (EEZ) boundary service.

Provides GeoJSON-based EEZ boundary data for jurisdiction detection.
Data source: marineregions.org (VLIZ) — freely available under CC-BY.

Zones are loaded from a local GeoJSON file or bundled simplified boundaries.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

_log = logging.getLogger("aegisais.geodata.eez")

# In-memory EEZ store: list of {name, sovereign, iso3, mrgid, polygon: [[lon, lat], ...]}
_eez_zones: list[dict[str, Any]] = []

# Bundled simplified EEZ boundaries for key NATO maritime areas.
# Full dataset from marineregions.org can be loaded via load_eez_geojson().
_BUNDLED_EEZ: list[dict[str, Any]] = [
    {
        "name": "United Kingdom EEZ",
        "sovereign": "United Kingdom",
        "iso3": "GBR",
        "mrgid": 5696,
        "bbox": [-13.0, 49.0, 3.0, 62.0],
    },
    {
        "name": "Norway EEZ",
        "sovereign": "Norway",
        "iso3": "NOR",
        "mrgid": 5698,
        "bbox": [-5.0, 56.0, 35.0, 72.0],
    },
    {
        "name": "Denmark EEZ",
        "sovereign": "Denmark",
        "iso3": "DNK",
        "mrgid": 5674,
        "bbox": [3.0, 54.0, 16.0, 58.0],
    },
    {
        "name": "Germany EEZ",
        "sovereign": "Germany",
        "iso3": "DEU",
        "mrgid": 5669,
        "bbox": [3.0, 53.5, 15.0, 55.5],
    },
    {
        "name": "Sweden EEZ",
        "sovereign": "Sweden",
        "iso3": "SWE",
        "mrgid": 5700,
        "bbox": [10.0, 55.0, 25.0, 66.0],
    },
    {
        "name": "Finland EEZ",
        "sovereign": "Finland",
        "iso3": "FIN",
        "mrgid": 5675,
        "bbox": [19.0, 59.0, 30.0, 66.0],
    },
    {
        "name": "Estonia EEZ",
        "sovereign": "Estonia",
        "iso3": "EST",
        "mrgid": 5673,
        "bbox": [21.0, 57.5, 28.0, 60.0],
    },
    {
        "name": "Latvia EEZ",
        "sovereign": "Latvia",
        "iso3": "LVA",
        "mrgid": 5690,
        "bbox": [19.0, 55.5, 24.0, 58.0],
    },
    {
        "name": "Lithuania EEZ",
        "sovereign": "Lithuania",
        "iso3": "LTU",
        "mrgid": 5691,
        "bbox": [19.0, 55.0, 22.0, 56.5],
    },
    {
        "name": "Poland EEZ",
        "sovereign": "Poland",
        "iso3": "POL",
        "mrgid": 5697,
        "bbox": [14.0, 54.0, 20.0, 56.0],
    },
    {
        "name": "Netherlands EEZ",
        "sovereign": "Netherlands",
        "iso3": "NLD",
        "mrgid": 5693,
        "bbox": [2.5, 51.0, 7.5, 56.0],
    },
    {
        "name": "France EEZ (Atlantic)",
        "sovereign": "France",
        "iso3": "FRA",
        "mrgid": 5677,
        "bbox": [-10.0, 42.0, 3.0, 51.5],
    },
    {
        "name": "Spain EEZ",
        "sovereign": "Spain",
        "iso3": "ESP",
        "mrgid": 5701,
        "bbox": [-12.0, 35.0, 5.0, 46.0],
    },
    {
        "name": "Italy EEZ",
        "sovereign": "Italy",
        "iso3": "ITA",
        "mrgid": 5688,
        "bbox": [6.0, 36.0, 19.0, 47.0],
    },
    {
        "name": "Greece EEZ",
        "sovereign": "Greece",
        "iso3": "GRC",
        "mrgid": 5679,
        "bbox": [19.0, 34.0, 30.0, 42.0],
    },
    {
        "name": "Turkey EEZ",
        "sovereign": "Turkey",
        "iso3": "TUR",
        "mrgid": 5703,
        "bbox": [25.0, 35.5, 42.0, 42.5],
    },
    {
        "name": "United States EEZ (Atlantic)",
        "sovereign": "United States",
        "iso3": "USA",
        "mrgid": 8456,
        "bbox": [-82.0, 24.0, -65.0, 45.0],
    },
    {
        "name": "Canada EEZ (Atlantic)",
        "sovereign": "Canada",
        "iso3": "CAN",
        "mrgid": 8491,
        "bbox": [-72.0, 41.0, -50.0, 63.0],
    },
    {
        "name": "Russia EEZ (Baltic)",
        "sovereign": "Russia",
        "iso3": "RUS",
        "mrgid": 5699,
        "bbox": [18.0, 54.0, 32.0, 61.0],
    },
]


def load_eez_geojson(path: Path) -> int:
    """Load EEZ boundaries from a marineregions.org GeoJSON file.

    Expected format: FeatureCollection with Polygon/MultiPolygon geometries.
    Each feature should have properties: GEONAME, SOVEREIGN1, ISO_SOV1, MRGID.

    Returns the number of zones loaded.
    """
    global _eez_zones
    with open(path) as f:
        fc = json.load(f)

    zones = []
    for feature in fc.get("features", []):
        props = feature.get("properties", {})
        geom = feature.get("geometry", {})

        if geom.get("type") not in ("Polygon", "MultiPolygon"):
            continue

        # For MultiPolygon, take the largest ring
        if geom["type"] == "MultiPolygon":
            coords = max(geom["coordinates"], key=lambda rings: len(rings[0]))
            polygon = coords[0]
        else:
            polygon = geom["coordinates"][0]

        # Compute bbox
        lons = [c[0] for c in polygon]
        lats = [c[1] for c in polygon]

        zones.append({
            "name": props.get("GEONAME", "Unknown"),
            "sovereign": props.get("SOVEREIGN1", "Unknown"),
            "iso3": props.get("ISO_SOV1", ""),
            "mrgid": props.get("MRGID", 0),
            "polygon": polygon,
            "bbox": [min(lons), min(lats), max(lons), max(lats)],
        })

    _eez_zones = zones
    _log.info("Loaded %d EEZ zones from %s", len(zones), path)
    return len(zones)


def get_eez_zones() -> list[dict[str, Any]]:
    """Return all loaded EEZ zones."""
    if _eez_zones:
        return _eez_zones
    return _BUNDLED_EEZ


def _point_in_bbox(lon: float, lat: float, bbox: list[float]) -> bool:
    """Check if a point is within a bounding box [min_lon, min_lat, max_lon, max_lat]."""
    return bbox[0] <= lon <= bbox[2] and bbox[1] <= lat <= bbox[3]


def _point_in_polygon(lon: float, lat: float, polygon: list[list[float]]) -> bool:
    """Ray-casting point-in-polygon test."""
    n = len(polygon)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if ((yi > lat) != (yj > lat)) and (lon < (xj - xi) * (lat - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def identify_eez(lon: float, lat: float) -> Optional[dict[str, Any]]:
    """Identify which EEZ a position falls within.

    Uses bbox pre-filter then polygon containment test for full GeoJSON zones,
    or bbox-only for bundled simplified boundaries.

    Returns zone metadata or None if in international waters.
    """
    zones = get_eez_zones()

    for zone in zones:
        bbox = zone.get("bbox")
        if bbox and not _point_in_bbox(lon, lat, bbox):
            continue

        polygon = zone.get("polygon")
        if polygon:
            if _point_in_polygon(lon, lat, polygon):
                return {
                    "name": zone["name"],
                    "sovereign": zone["sovereign"],
                    "iso3": zone["iso3"],
                    "mrgid": zone.get("mrgid"),
                }
        else:
            # bbox-only (bundled data) — approximate match
            return {
                "name": zone["name"],
                "sovereign": zone["sovereign"],
                "iso3": zone["iso3"],
                "mrgid": zone.get("mrgid"),
            }

    return None  # International waters


def check_flag_eez_mismatch(
    lon: float,
    lat: float,
    vessel_flag_iso3: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    """Check if a vessel is operating outside its flag state's EEZ.

    Useful for sanctions evasion and illegal fishing detection.
    """
    if not vessel_flag_iso3:
        return None

    eez = identify_eez(lon, lat)
    if eez is None:
        return None  # International waters — no jurisdiction issue

    if eez["iso3"] == vessel_flag_iso3:
        return None  # Vessel in own EEZ

    return {
        "type": "FLAG_EEZ_MISMATCH",
        "vessel_flag": vessel_flag_iso3,
        "eez": eez,
        "note": f"Vessel flagged {vessel_flag_iso3} operating in {eez['sovereign']} EEZ",
    }
