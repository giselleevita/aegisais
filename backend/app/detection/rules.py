from dataclasses import asdict
from typing import Any
from ..settings import settings
from ..ingest.loaders import AisPoint
from ..tracking.features import implied_speed_knots, heading_delta_deg, haversine_m, mps_to_knots

def rule_teleport(p1: AisPoint, p2: AisPoint) -> dict[str, Any] | None:
    """
    Gap-aware teleport detection with tiered thresholds.
    - Short gap (≤120s): 60 kn threshold
    - Medium gap (120s-30min): 100 kn threshold
    - Long gap (30-60min): Data gap flag only
    """
    import logging
    log = logging.getLogger("aegisais.detection")
    
    dt = (p2.timestamp - p1.timestamp).total_seconds()
    if dt <= 0:
        log.debug("TELEPORT: dt <= 0 (dt=%.2f)", dt)
        return None
    
    # Determine threshold based on time gap
    if dt <= settings.teleport_dt_short_max_sec:
        threshold = settings.teleport_speed_knots_short
        tier = "short"
    elif dt <= settings.teleport_dt_medium_max_sec:
        threshold = settings.teleport_speed_knots_medium
        tier = "medium"
    elif dt <= settings.teleport_dt_long_max_sec:
        # Long gap: only flag as data gap, not teleport
        sp = implied_speed_knots(p1, p2)
        if sp is None:
            return None
        # Only alert if speed is extremely high (likely still teleport)
        if sp > settings.teleport_speed_knots_medium * 2:  # 200+ knots
            d = haversine_m(p1.lat, p1.lon, p2.lat, p2.lon)
            severity = 30  # Low confidence for long gaps
            return {
                "type": "TELEPORT",
                "severity": severity,
                "summary": f"Large gap ({dt/60:.1f} min) with high speed {sp:.1f} kn",
                "evidence": {"p1": asdict(p1), "p2": asdict(p2), "dt_sec": dt, "distance_m": d, "implied_speed_kn": sp, "tier": "long_gap"},
            }
        return None
    else:
        # dt > 60 minutes: skip (likely legitimate data gap)
        log.debug("TELEPORT: dt too large (dt=%.1f min > %d min)", dt/60, settings.teleport_dt_long_max_sec/60)
        return None

    sp = implied_speed_knots(p1, p2)
    if sp is None:
        log.debug("TELEPORT: Could not calculate speed")
        return None

    log.debug("TELEPORT: speed=%.1f kn, threshold=%.1f kn (tier=%s)", sp, threshold, tier)
    
    if sp > threshold:
        d = haversine_m(p1.lat, p1.lon, p2.lat, p2.lon)
        severity = min(100, int(100 * (sp - threshold) / threshold))
        log.info("TELEPORT ALERT: speed=%.1f kn > threshold=%.1f kn (tier=%s), severity=%d", sp, threshold, tier, severity)
        return {
            "type": "TELEPORT",
            "severity": severity,
            "summary": f"Implied speed {sp:.1f} kn exceeds threshold ({tier} gap)",
            "evidence": {"p1": asdict(p1), "p2": asdict(p2), "dt_sec": dt, "distance_m": d, "implied_speed_kn": sp, "tier": tier},
        }
    return None


def rule_teleport_t2(p1: AisPoint, p2: AisPoint) -> dict[str, Any] | None:
    """
    Tier‑2 teleport: suspicious medium/long‑gap jumps below Tier‑1 thresholds.
    Lower‑severity data‑quality signal.
    """
    import logging
    log = logging.getLogger("aegisais.detection")

    dt = (p2.timestamp - p1.timestamp).total_seconds()
    if dt <= 0:
        return None

    # Only consider up to the medium window for Tier‑2
    if dt > settings.teleport_dt_medium_max_sec:
        return None

    sp = implied_speed_knots(p1, p2)
    if sp is None:
        return None

    # For short gaps (<= 120s), suspicious band 40‑60 kn (Tier‑1 fires above 60)
    if dt <= settings.teleport_dt_short_max_sec:
        low = settings.teleport_suspicious_min_knots
        high = settings.teleport_speed_knots_short
        band_name = "short"
    else:
        # For 2–30 min, suspicious band 60‑100 kn (Tier‑1 fires above 100)
        low = settings.teleport_speed_knots_short
        high = settings.teleport_speed_knots_medium
        band_name = "medium"

    # Outside Tier‑2 band, or already extreme enough for Tier‑1
    if sp <= low or sp >= high:
        return None

    d_m = haversine_m(p1.lat, p1.lon, p2.lat, p2.lon)
    frac = (sp - low) / max(1.0, (high - low))
    severity = 20 + int(40 * frac)  # 20‑60

    log.info(
        "TELEPORT_T2 ALERT: speed=%.1f kn in %s gap (band %.1f‑%.1f kn), severity=%d",
        sp,
        band_name,
        low,
        high,
        severity,
    )
    return {
        "type": "TELEPORT_T2",
        "severity": severity,
        "summary": f"Suspicious jump {sp:.1f} kn over {dt:.0f}s (Tier‑2 teleport)",
        "evidence": {
            "p1": asdict(p1),
            "p2": asdict(p2),
            "dt_sec": dt,
            "distance_m": d_m,
            "implied_speed_kn": sp,
            "tier": "suspicious",
            "band": band_name,
            "band_low_kn": low,
            "band_high_kn": high,
        },
    }


def rule_turn_rate(p1: AisPoint, p2: AisPoint) -> dict[str, Any] | None:
    """
    Turn rate detection using COG when heading is missing/unreliable.
    Uses confidence tiers based on speed.
    """
    import logging
    log = logging.getLogger("aegisais.detection")

    dt = (p2.timestamp - p1.timestamp).total_seconds()
    if dt <= 0:
        return None

    # Skip if dt too small (noise)
    if dt < settings.turn_rate_dt_min_sec:
        log.debug("TURN_RATE: dt too small (dt=%.2f < %.2f)", dt, settings.turn_rate_dt_min_sec)
        return None

    # Prefer COG over heading (more reliable in AIS)
    # Use heading only if both are valid and heading is changing plausibly
    use_heading = False
    angle_change: float | None = None

    # Check if heading is available and valid (not stuck/not available)
    heading_valid = (
        p1.heading is not None
        and p2.heading is not None
        and p1.heading != 511
        and p2.heading != 511  # 511 = "not available" in AIS
    )

    # Check if COG is available
    cog_available = p1.cog is not None and p2.cog is not None

    if heading_valid and cog_available:
        # If both available, prefer heading if it's changing (not stuck)
        heading_change = heading_delta_deg(p1.heading, p2.heading)
        cog_change = heading_delta_deg(p1.cog, p2.cog)
        if heading_change > 0.1 or cog_change < 0.1:
            use_heading = True
            angle_change = heading_change
        else:
            angle_change = cog_change
    elif heading_valid:
        use_heading = True
        angle_change = heading_delta_deg(p1.heading, p2.heading)
    elif cog_available:
        angle_change = heading_delta_deg(p1.cog, p2.cog)
    else:
        log.debug("TURN_RATE: No heading or COG data")
        return None

    # Calculate speed (use SOG if present, else implied)
    sog = p2.sog
    if sog is None:
        sog = implied_speed_knots(p1, p2)
    if sog is None:
        return None

    # Confidence tiers based on speed
    if sog < settings.min_speed_for_turn_check_low_knots:
        # Too slow, skip
        log.debug(
            "TURN_RATE: Speed too low (%.1f < %.1f kn)",
            sog,
            settings.min_speed_for_turn_check_low_knots,
        )
        return None
    elif sog < settings.min_speed_for_turn_check_knots:
        # Low speed: reduced sensitivity (higher threshold, lower severity cap)
        max_rate = settings.max_turn_rate_deg_per_sec * 1.5  # 4.5 deg/s
        severity_cap = 50
        tier = "low_speed"
    else:
        # Normal speed: full sensitivity
        max_rate = settings.max_turn_rate_deg_per_sec
        severity_cap = 100
        tier = "normal"

    rate = angle_change / dt  # type: ignore[operator]
    log.debug(
        "TURN_RATE: rate=%.2f deg/s, threshold=%.2f deg/s, speed=%.1f kn (tier=%s)",
        rate,
        max_rate,
        sog,
        tier,
    )

    if rate > max_rate:
        severity = min(severity_cap, int(severity_cap * (rate - max_rate) / max_rate))
        angle_type = "heading" if use_heading else "COG"
        log.info(
            "TURN_RATE ALERT: rate=%.2f deg/s > threshold=%.2f deg/s, severity=%d",
            rate,
            max_rate,
            severity,
        )
        return {
            "type": "TURN_RATE",
            "severity": severity,
            "summary": f"Turn rate {rate:.2f} deg/s at {sog:.1f} kn ({angle_type})",
            "evidence": {
                "dt_sec": dt,
                "delta_angle_deg": angle_change,
                "turn_rate_deg_s": rate,
                "speed_kn": sog,
                "angle_type": angle_type,
                "tier": tier,
            },
        }
    return None


def rule_turn_rate_t2(p1: AisPoint, p2: AisPoint) -> dict[str, Any] | None:
    """
    Tier‑2 turn‑rate: moderate but suspicious turns below Tier‑1 threshold.
    Higher‑volume, lower‑severity data‑quality signal.
    """
    import logging
    log = logging.getLogger("aegisais.detection")

    dt = (p2.timestamp - p1.timestamp).total_seconds()
    if dt <= 0 or dt < settings.turn_rate_dt_min_sec:
        return None

    # Same heading/COG selection as Tier‑1
    use_heading = False
    angle_change: float | None = None

    heading_valid = (
        p1.heading is not None
        and p2.heading is not None
        and p1.heading != 511
        and p2.heading != 511
    )
    cog_available = p1.cog is not None and p2.cog is not None

    if heading_valid and cog_available:
        heading_change = heading_delta_deg(p1.heading, p2.heading)
        cog_change = heading_delta_deg(p1.cog, p2.cog)
        if heading_change > 0.1 or cog_change < 0.1:
            use_heading = True
            angle_change = heading_change
        else:
            angle_change = cog_change
    elif heading_valid:
        use_heading = True
        angle_change = heading_delta_deg(p1.heading, p2.heading)
    elif cog_available:
        angle_change = heading_delta_deg(p1.cog, p2.cog)
    else:
        return None

    sog = p2.sog
    if sog is None:
        sog = implied_speed_knots(p1, p2)
    if sog is None or sog < settings.min_speed_for_turn_check_low_knots:
        return None

    suspicious_min = settings.turn_rate_suspicious_min_deg_per_sec
    tier1_threshold = settings.max_turn_rate_deg_per_sec

    rate = angle_change / dt  # type: ignore[operator]

    # Only fire in moderate band [suspicious_min, tier1_threshold)
    if rate <= suspicious_min or rate >= tier1_threshold:
        return None

    frac = (rate - suspicious_min) / max(0.5, (tier1_threshold - suspicious_min))
    severity = 15 + int(35 * frac)  # 15‑50
    angle_type = "heading" if use_heading else "COG"

    log.info(
        "TURN_RATE_T2 ALERT: rate=%.2f deg/s (band %.1f‑%.1f), speed=%.1f kn, severity=%d",
        rate,
        suspicious_min,
        tier1_threshold,
        sog,
        severity,
    )
    return {
        "type": "TURN_RATE_T2",
        "severity": severity,
        "summary": f"Moderate suspicious turn {rate:.2f} deg/s at {sog:.1f} kn (Tier‑2)",
        "evidence": {
            "dt_sec": dt,
            "delta_angle_deg": angle_change,
            "turn_rate_deg_s": rate,
            "speed_kn": sog,
            "angle_type": angle_type,
            "tier": "suspicious",
            "band_low_deg_s": suspicious_min,
            "band_high_deg_s": tier1_threshold,
        },
    }


def rule_position_invalid(p1: AisPoint, p2: AisPoint) -> dict[str, Any] | None:
    """
    Basic position sanity checks:
    - Out-of-bounds latitude/longitude
    - (0,0) or very close
    - Unchanged position for a long time while SOG says we're moving
    """
    # Out of bounds
    if not (-90 <= p2.lat <= 90) or not (-180 <= p2.lon <= 180):
        return {
            "type": "POSITION_INVALID",
            "severity": 100,
            "summary": f"Position out of bounds: lat={p2.lat}, lon={p2.lon}",
            "evidence": {"lat": p2.lat, "lon": p2.lon, "mmsi": p2.mmsi},
        }

    # (0,0) is almost always bogus
    if abs(p2.lat) < 0.001 and abs(p2.lon) < 0.001:
        return {
            "type": "POSITION_INVALID",
            "severity": 100,
            "summary": "Position at or near (0, 0)",
            "evidence": {"lat": p2.lat, "lon": p2.lon, "mmsi": p2.mmsi},
        }

    # Same position for a long time while SOG says we're moving
    if p1.lat == p2.lat and p1.lon == p2.lon:
        dt = (p2.timestamp - p1.timestamp).total_seconds()
        if dt > 60 and p2.sog is not None and p2.sog > 1.0:
            return {
                "type": "POSITION_INVALID",
                "severity": 70,
                "summary": f"Position unchanged for {dt:.0f}s while SOG={p2.sog:.1f} kn",
                "evidence": {"dt_sec": dt, "sog": p2.sog, "lat": p2.lat, "lon": p2.lon},
            }

    # Extreme outlier distance (very rough guardrail)
    d_m = haversine_m(p1.lat, p1.lon, p2.lat, p2.lon)
    if d_m > settings.position_outlier_distance_km * 1000:
        dt = (p2.timestamp - p1.timestamp).total_seconds()
        sp = implied_speed_knots(p1, p2)
        if sp is not None and sp > 1000:  # only flag if speed is extreme too
            return {
                "type": "POSITION_INVALID",
                "severity": 90,
                "summary": f"Extreme position jump: {d_m/1000:.1f} km in {dt:.0f}s",
                "evidence": {"distance_m": d_m, "dt_sec": dt, "implied_speed_kn": sp},
            }

    return None


def rule_acceleration(p1: AisPoint, p2: AisPoint) -> dict[str, Any] | None:
    """
    Detects impossible acceleration/deceleration and SOG vs implied-speed mismatch.
    """
    dt = (p2.timestamp - p1.timestamp).total_seconds()
    if dt <= 0 or dt > 300:  # only consider up to 5 minutes
        return None

    # Implied speed from distance / dt
    implied_sp = implied_speed_knots(p1, p2)
    if implied_sp is None:
        return None

    # SOG vs implied speed mismatch
    if p2.sog is not None:
        diff = abs(implied_sp - p2.sog)
        if diff > settings.sog_implied_speed_diff_threshold_knots:
            severity = min(
                100,
                int(100 * diff / settings.sog_implied_speed_diff_threshold_knots),
            )
            return {
                "type": "ACCELERATION",
                "severity": severity,
                "summary": f"SOG mismatch: reported {p2.sog:.1f} kn vs implied {implied_sp:.1f} kn",
                "evidence": {
                    "sog_reported": p2.sog,
                    "implied_speed_kn": implied_sp,
                    "difference_kn": diff,
                    "dt_sec": dt,
                },
            }

    # Acceleration based purely on SOG
    if p1.sog is not None and p2.sog is not None:
        accel = abs(p2.sog - p1.sog) / dt  # knots per second
        if accel > settings.max_accel_knots_per_sec:
            severity = min(
                100,
                int(100 * accel / settings.max_accel_knots_per_sec),
            )
            return {
                "type": "ACCELERATION",
                "severity": severity,
                "summary": f"Impossible acceleration: {accel:.2f} kn/s",
                "evidence": {
                    "accel_knots_per_sec": accel,
                    "sog1": p1.sog,
                    "sog2": p2.sog,
                    "dt_sec": dt,
                },
            }

    return None


def rule_heading_cog_consistency(p1: AisPoint, p2: AisPoint) -> dict[str, Any] | None:
    """
    Detects wild heading/COG changes at high speed (teleport-turn style anomalies).
    """
    dt = (p2.timestamp - p1.timestamp).total_seconds()
    if dt <= 0 or dt > 10:  # only consider short intervals
        return None

    # Speed from SOG or implied
    sog = p2.sog
    if sog is None:
        sog = implied_speed_knots(p1, p2)
    if sog is None or sog < 15.0:
        return None

    # Combine heading + COG where available
    angle_change: float | None = None
    angle_type = "unknown"

    if (
        p1.heading is not None
        and p2.heading is not None
        and p1.heading != 511
        and p2.heading != 511
    ):
        angle_change = heading_delta_deg(p1.heading, p2.heading)
        angle_type = "heading"

    if p1.cog is not None and p2.cog is not None:
        cog_change = heading_delta_deg(p1.cog, p2.cog)
        if angle_change is None or cog_change > angle_change:
            angle_change = cog_change
            angle_type = "COG"

    if angle_change is None:
        return None

    rate = angle_change / dt
    if rate > settings.max_turn_rate_high_speed_deg_per_sec:
        severity = min(
            100,
            int(
                100
                * (rate - settings.max_turn_rate_high_speed_deg_per_sec)
                / settings.max_turn_rate_high_speed_deg_per_sec
            ),
        )
        return {
            "type": "HEADING_COG_CONSISTENCY",
            "severity": severity,
            "summary": f"Wild {angle_type} change: {rate:.2f} deg/s at {sog:.1f} kn",
            "evidence": {
                "turn_rate_deg_s": rate,
                "speed_kn": sog,
                "angle_type": angle_type,
                "angle_change_deg": angle_change,
                "dt_sec": dt,
            },
        }

    return None
