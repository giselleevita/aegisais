import math
from ..ingest.loaders import AisPoint

EARTH_R = 6371000.0  # meters

def haversine_m(lat1, lon1, lat2, lon2) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dl/2)**2
    return 2 * EARTH_R * math.asin(math.sqrt(a))

def mps_to_knots(mps: float) -> float:
    return mps * 1.9438444924406

def heading_delta_deg(h1: float, h2: float) -> float:
    # smallest angle difference [0..180]
    d = abs((h2 - h1) % 360.0)
    return min(d, 360.0 - d)

def implied_speed_knots(p1: AisPoint, p2: AisPoint) -> float | None:
    dt = (p2.timestamp - p1.timestamp).total_seconds()
    if dt <= 0:
        return None
    d = haversine_m(p1.lat, p1.lon, p2.lat, p2.lon)
    return mps_to_knots(d / dt)
