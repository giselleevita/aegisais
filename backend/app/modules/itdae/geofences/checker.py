"""
Point-in-polygon checker for ITDAE geofence zones.
Uses the ray-casting algorithm (no external dependencies).
"""
from typing import Optional
from .baltic_cables import BALTIC_CABLE_ZONES


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


def get_zone_for_position(lon: float, lat: float) -> Optional[dict]:
    """
    Check if a position falls within any defined Baltic cable geofence zone.

    Args:
        lon: Longitude of the vessel position
        lat: Latitude of the vessel position

    Returns:
        The matching zone dict (id, name, description, risk_level) or None
    """
    for zone in BALTIC_CABLE_ZONES:
        if _point_in_polygon(lon, lat, zone["polygon"]):
            return {
                "id": zone["id"],
                "name": zone["name"],
                "description": zone["description"],
                "risk_level": zone["risk_level"],
            }
    return None


def get_all_zones_for_position(lon: float, lat: float) -> list[dict]:
    """
    Return ALL zones a position falls within (in case of overlapping zones).
    """
    matches = []
    for zone in BALTIC_CABLE_ZONES:
        if _point_in_polygon(lon, lat, zone["polygon"]):
            matches.append({
                "id": zone["id"],
                "name": zone["name"],
                "description": zone["description"],
                "risk_level": zone["risk_level"],
            })
    return matches
