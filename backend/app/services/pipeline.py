import logging
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from ..models import VesselLatest, Alert
from ..ingest.loaders import AisPoint
from ..tracking.track_store import TrackStore
from ..settings import settings
from ..detection.rules import (
    rule_teleport,
    rule_teleport_t2,
    rule_turn_rate,
    rule_turn_rate_t2,
    rule_position_invalid,
    rule_acceleration,
    rule_heading_cog_consistency,
)

log = logging.getLogger("aegisais.pipeline")
_track_store = TrackStore(window_size=5)

# Alert cooldown tracking: (MMSI, rule_type) -> last_alert_timestamp
_alert_cooldowns: dict[tuple[str, str], float] = {}

def process_point(db: Session, p: AisPoint) -> list[dict]:
    """
    - Update latest vessel position
    - Run detectors using last track points
    - Persist alerts
    
    Returns list of new alerts (as dicts) generated from this point.
    """
    try:
        tw = _track_store.push(p)
        pts = list(tw.points)

        # upsert vessel latest
        v = db.query(VesselLatest).filter(VesselLatest.mmsi == p.mmsi).first()
        if v is None:
            v = VesselLatest(
                mmsi=p.mmsi,
                timestamp=p.timestamp,
                lat=p.lat,
                lon=p.lon,
                sog=p.sog,
                cog=p.cog,
                heading=p.heading,
                last_alert_severity=0
            )
            db.add(v)
        else:
            v.timestamp = p.timestamp
            v.lat = p.lat
            v.lon = p.lon
            v.sog = p.sog
            v.cog = p.cog
            v.heading = p.heading

        new_alerts: list[dict] = []
        if len(pts) >= 2:
            p1, p2 = pts[-2], pts[-1]
            log.debug("Checking rules for MMSI %s: %d points in track, comparing p1 (t=%s) to p2 (t=%s)", 
                     p.mmsi, len(pts), p1.timestamp, p2.timestamp)
            # Run all detection rules
            for rule in (
                rule_position_invalid,  # Tier‑1 integrity
                rule_teleport,          # Tier‑1 teleport
                rule_teleport_t2,       # Tier‑2 suspicious teleport
                rule_turn_rate,         # Tier‑1 turn rate
                rule_turn_rate_t2,      # Tier‑2 suspicious turn rate
                rule_acceleration,      # Tier‑2 data‑quality
                rule_heading_cog_consistency,  # Tier‑1 high‑speed heading/COG
            ):
                try:
                    res = rule(p1, p2)
                    if res:
                        # Check cooldown (prevent spam)
                        cooldown_key = (p2.mmsi, res["type"])
                        last_alert_time = _alert_cooldowns.get(cooldown_key, 0)
                        current_time = p2.timestamp.timestamp()
                        time_since_last = current_time - last_alert_time
                        
                        if time_since_last < settings.alert_cooldown_sec:
                            log.debug("Alert %s for MMSI %s in cooldown (%.1f s < %d s)", 
                                     res["type"], p2.mmsi, time_since_last, settings.alert_cooldown_sec)
                            continue
                        
                        # Update cooldown
                        _alert_cooldowns[cooldown_key] = current_time
                        
                        log.info("Alert triggered: %s for MMSI %s - %s", res["type"], p2.mmsi, res["summary"])
                        a = Alert(
                            timestamp=p2.timestamp,
                            mmsi=p2.mmsi,
                            type=res["type"],
                            severity=int(res["severity"]),
                            summary=res["summary"],
                            evidence=res["evidence"],
                        )
                        db.add(a)
                        new_alerts.append(
                            {
                                "timestamp": p2.timestamp.isoformat(),
                                "mmsi": p2.mmsi,
                                "type": res["type"],
                                "severity": int(res["severity"]),
                                "summary": res["summary"],
                                "evidence": res["evidence"],
                            }
                        )
                        v.last_alert_severity = max(v.last_alert_severity or 0, int(res["severity"]))
                    else:
                        log.debug("Rule %s returned None for MMSI %s", rule.__name__, p.mmsi)
                except Exception as e:
                    log.warning("Error applying rule %s to points: %s", rule.__name__, e, exc_info=True)
                    continue
        else:
            log.debug("Not enough points for MMSI %s: only %d points in track", p.mmsi, len(pts))

        return new_alerts
    except SQLAlchemyError as e:
        log.error("Database error processing point for MMSI %s: %s", p.mmsi, e, exc_info=True)
        raise
    except Exception as e:
        log.error("Unexpected error processing point for MMSI %s: %s", p.mmsi, e, exc_info=True)
        raise
