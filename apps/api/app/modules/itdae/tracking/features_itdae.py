"""
ITDAE-specific trajectory feature calculations.
Extends app.tracking.features with additional metrics for
infrastructure threat detection (loitering, proximity to cable zones, etc.)

Reuses haversine_m, mps_to_knots, heading_delta_deg from the base module.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from app.tracking.features import haversine_m, mps_to_knots, heading_delta_deg

# ── Constants ─────────────────────────────────────────────────────────────────

EARTH_R = 6371000.0          # metres
NM_TO_M = 1852.0             # 1 nautical mile in metres

# Thresholds used by ITDAE detection rules (may be overridden by settings)
LOITER_MAX_SPEED_KN  = 3.0   # Below this = considered loitering
LOITER_MIN_RADIUS_M  = 926.0 # 0.5 nm radius — must stay within this area
LOITER_MIN_DURATION_S = 1800 # 30 min minimum for a loiter window
SLOW_TRANSIT_MAX_KN  = 5.0   # Suspiciously slow near cable zone


# ── Data structures ───────────────────────────────────────────────────────────

@dataclass
class ItdaePoint:
    """Lightweight AIS point used in ITDAE pipeline (from aisstream.io messages)."""
    mmsi: str
    timestamp: datetime
    lat: float
    lon: float
    speed: Optional[float] = None      # SOG knots
    course: Optional[float] = None     # COG degrees
    heading: Optional[float] = None    # True heading
    nav_status: Optional[int] = None   # AIS nav status (0=UW engine, 5=moored…)
    msg_type: Optional[int] = None     # AIS message type


@dataclass
class TrajectoryFeatures:
    """
    Computed features between two consecutive ItdaePoints.
    Used as input to ITDAE detection rules.
    """
    mmsi: str
    t1: datetime
    t2: datetime
    dt_sec: float
    dist_m: float
    implied_speed_kn: float
    reported_speed_kn: Optional[float]    # from SOG field
    speed_delta_kn: Optional[float]       # |implied - reported|
    turn_rate_deg_per_sec: Optional[float]
    heading_delta_deg: Optional[float]
    is_loitering: bool                    # based on speed + radius
    in_geofence: bool                     # set by caller after geofence check


# ── Core computations ─────────────────────────────────────────────────────────

def implied_speed_knots_itdae(p1: ItdaePoint, p2: ItdaePoint) -> Optional[float]:
    """Compute implied speed between two ItdaePoints."""
    dt = (p2.timestamp - p1.timestamp).total_seconds()
    if dt <= 0:
        return None
    d = haversine_m(p1.lat, p1.lon, p2.lat, p2.lon)
    return mps_to_knots(d / dt)


def turn_rate_deg_per_sec(p1: ItdaePoint, p2: ItdaePoint) -> Optional[float]:
    """
    Compute turn rate (degrees/sec) between two points using COG.
    Returns None if COG missing or dt too small.
    """
    if p1.course is None or p2.course is None:
        return None
    dt = (p2.timestamp - p1.timestamp).total_seconds()
    if dt < 2.0:
        return None
    delta = heading_delta_deg(p1.course, p2.course)
    return delta / dt


def is_loitering(
    points: list[ItdaePoint],
    max_speed_kn: float = LOITER_MAX_SPEED_KN,
    min_radius_m: float = LOITER_MIN_RADIUS_M,
    min_duration_s: float = LOITER_MIN_DURATION_S,
) -> bool:
    """
    Determine if a track window indicates loitering behavior.

    Conditions:
    1. Window spans at least `min_duration_s` seconds
    2. All points are within `min_radius_m` of the centroid
    3. Average implied speed is below `max_speed_kn`

    Args:
        points: Ordered list of ItdaePoints (at least 2)
        max_speed_kn: Speed threshold for loitering
        min_radius_m: Max radius from centroid to still be considered loitering
        min_duration_s: Minimum duration window in seconds

    Returns:
        True if loitering criteria are met
    """
    if len(points) < 2:
        return False

    duration = (points[-1].timestamp - points[0].timestamp).total_seconds()
    if duration < min_duration_s:
        return False

    # Check average implied speed
    speeds = []
    for i in range(1, len(points)):
        s = implied_speed_knots_itdae(points[i - 1], points[i])
        if s is not None:
            speeds.append(s)
    if not speeds or (sum(speeds) / len(speeds)) > max_speed_kn:
        return False

    # Check spatial spread — all points within min_radius_m of centroid
    avg_lat = sum(p.lat for p in points) / len(points)
    avg_lon = sum(p.lon for p in points) / len(points)
    for p in points:
        if haversine_m(avg_lat, avg_lon, p.lat, p.lon) > min_radius_m:
            return False

    return True


def compute_trajectory_features(
    p1: ItdaePoint,
    p2: ItdaePoint,
    window: list[ItdaePoint],
) -> TrajectoryFeatures:
    """
    Compute all trajectory features between p1→p2 with context from the window.

    Args:
        p1: Previous point
        p2: Current point
        window: Recent track window (including p1, p2) for loiter check

    Returns:
        TrajectoryFeatures dataclass
    """
    dt = (p2.timestamp - p1.timestamp).total_seconds()
    dist = haversine_m(p1.lat, p1.lon, p2.lat, p2.lon)
    imp_spd = implied_speed_knots_itdae(p1, p2) or 0.0
    rep_spd = p2.speed
    spd_delta = abs(imp_spd - rep_spd) if rep_spd is not None else None
    tr = turn_rate_deg_per_sec(p1, p2)
    hd = heading_delta_deg(p1.heading, p2.heading) if (p1.heading and p2.heading) else None
    loiter = is_loitering(window)

    return TrajectoryFeatures(
        mmsi=p1.mmsi,
        t1=p1.timestamp,
        t2=p2.timestamp,
        dt_sec=dt,
        dist_m=dist,
        implied_speed_kn=imp_spd,
        reported_speed_kn=rep_spd,
        speed_delta_kn=spd_delta,
        turn_rate_deg_per_sec=tr,
        heading_delta_deg=hd,
        is_loitering=loiter,
        in_geofence=False,  # caller sets this after geofence check
    )
