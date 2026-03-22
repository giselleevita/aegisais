"""
Point-in-polygon checker for ITDAE geofence zones.
Uses the ray-casting algorithm (no external dependencies).
"""
from typing import Optional

from .zones_service import get_active_zones_for_checker


def _point_in_polygon(lon: float, lat: float, polygon: list[list[float]]) -> bool:
    """
    Ray-casting algorithm to determine if a point is inside a polygon.

    Args:
        lon: Longitude of the point
        lat: Latitude of the point
        polygon: List of [lon, lat] coordinate pairs (closed ring)

    Returns:
        True if the point is inside the polygon
    """
    n = len(polygon)
    inside = False
    px, py = lon, lat
    j = n - 1

    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if ((yi > py) != (yj > py)) and (px < (xj - xi) * (py - yi) / (yj - yi) + xi):
            inside = not inside
        j = i

    return inside


def get_zone_for_position(
    lon: float,
    lat: float,
    zones: Optional[list[dict]] = None,
) -> Optional[dict]:
    """
    Check if a position falls within any defined geofence zone.

    Args:
        lon: Longitude of the vessel position
        lat: Latitude of the vessel position
        zones: Optional pre-loaded zone dicts (id, name, description, risk_level, polygon).
               If omitted, loads active zones via DB + Redis cache.

    Returns:
        The first matching zone dict (id, name, description, risk_level) or None
    """
    if zones is None:
        zones = get_active_zones_for_checker()
    for zone in zones:
        if _point_in_polygon(lon, lat, zone["polygon"]):
            return {
                "id": zone["id"],
                "name": zone["name"],
                "description": zone["description"],
                "risk_level": zone["risk_level"],
            }
    return None


def get_all_zones_for_position(
    lon: float,
    lat: float,
    zones: Optional[list[dict]] = None,
) -> list[dict]:
    """
    Return ALL zones a position falls within (in case of overlapping zones).
    """
    if zones is None:
        zones = get_active_zones_for_checker()
    matches = []
    for zone in zones:
        if _point_in_polygon(lon, lat, zone["polygon"]):
            matches.append({
                "id": zone["id"],
                "name": zone["name"],
                "description": zone["description"],
                "risk_level": zone["risk_level"],
            })
    return matches
