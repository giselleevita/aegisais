import logging
from app.infrastructure.ingest.loaders import AisPoint
from app.infrastructure.cache.track_store import RedisTrackStore
from app.infrastructure.cache.cooldown_store import RedisCooldownStore
from app.core.config import settings
from app.detection.rules import (
    rule_teleport,
    rule_teleport_t2,
    rule_turn_rate,
    rule_turn_rate_t2,
    rule_position_invalid,
    rule_acceleration,
    rule_heading_cog_consistency,
)
from app.infrastructure.messaging import publisher
from app.modules.fusion.fused_rules import rule_surface_activity_near_cable_segment

log = logging.getLogger("aegisais.pipeline")

# Redis-backed stores — stateless, multi-pod safe
_track_store = RedisTrackStore(window_size_min=60)
_cooldown_store = RedisCooldownStore()

def enqueue_point(p: AisPoint):
    """
    Asynchronously push an AIS point to the processing stream.
    This is the fast-path for API ingestion.
    """
    publisher.publish(settings.stream_ais_raw, {
        "mmsi": p.mmsi,
        "timestamp": p.timestamp.isoformat(),
        "lat": p.lat,
        "lon": p.lon,
        "sog": p.sog,
        "cog": p.cog,
        "heading": p.heading
    })

def process_point(p: AisPoint) -> dict:
    """
    Pure logic function to run detection rules.
    Does NOT interact with the database.
    Interacts with Redis for track history and cooldowns.
    
    Returns:
        dict: {
            "point": dict,    # The AIS point data
            "alerts": list    # Any generated alerts
        }
    """
    try:
        _track_store.push(p)
        pts = _track_store.get_track(p.mmsi, limit=5)

        new_alerts: list[dict] = []
        max_severity = 0

        if len(pts) >= 2:
            p1, p2 = pts[-2], pts[-1]
            log.debug("Checking rules for MMSI %s: %d points in track", p.mmsi, len(pts))
            
            # Run all detection rules
            for rule in (
                rule_position_invalid,
                rule_teleport,
                rule_teleport_t2,
                rule_turn_rate,
                rule_turn_rate_t2,
                rule_acceleration,
                rule_heading_cog_consistency,
                rule_surface_activity_near_cable_segment,
            ):
                try:
                    res = rule(p1, p2)
                    if res:
                        # Redis-based cooldown check
                        if not _cooldown_store.check_and_set(p2.mmsi, res["type"]):
                            continue
                        
                        # Reduce evidence bloat
                        evidence = res.get("evidence", {})
                        if isinstance(evidence, dict):
                            slim_evidence = {
                                "dt_sec": evidence.get("dt_sec"),
                                "distance_m": evidence.get("distance_m"),
                                "implied_speed_kn": evidence.get("implied_speed_kn"),
                                "turn_rate_deg_per_sec": evidence.get("turn_rate_deg_per_sec"),
                                "accel_knots_per_sec": evidence.get("accel_knots_per_sec"),
                                "tier": evidence.get("tier"),
                                "p1_lat": p1.lat,
                                "p1_lon": p1.lon,
                                "p1_timestamp": p1.timestamp.isoformat(),
                                "p2_lat": p2.lat,
                                "p2_lon": p2.lon,
                                "p2_timestamp": p2.timestamp.isoformat(),
                                "p2_sog": p2.sog,
                                "p2_cog": p2.cog,
                                "p2_heading": p2.heading,
                            }
                            for key in ["reason", "sog_diff", "implied_speed", "heading_delta", "cog_delta"]:
                                if key in evidence:
                                    slim_evidence[key] = evidence[key]
                        else:
                            slim_evidence = evidence
                        
                        severity = int(res["severity"])
                        max_severity = max(max_severity, severity)
                        
                        alert_data = {
                            "timestamp": p2.timestamp.isoformat(),
                            "mmsi": p2.mmsi,
                            "type": res["type"],
                            "severity": severity,
                            "summary": res["summary"],
                            "evidence": slim_evidence,
                        }
                        new_alerts.append(alert_data)
                        log.info("Alert triggered: %s for MMSI %s", res["type"], p2.mmsi)
                except Exception as e:
                    log.warning("Error applying rule %s: %s", rule.__name__, e)
                    continue
        
        return {
            "point": {
                "mmsi": p.mmsi,
                "timestamp": p.timestamp.isoformat(),
                "lat": p.lat,
                "lon": p.lon,
                "sog": p.sog,
                "cog": p.cog,
                "heading": p.heading,
                "last_alert_severity": max_severity
            },
            "alerts": new_alerts
        }

    except Exception as e:
        log.error("Error processing point for MMSI %s: %s", p.mmsi, e, exc_info=True)
        raise
