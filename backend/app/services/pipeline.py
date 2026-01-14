import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from ..models import VesselLatest, Alert, AlertCooldown
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

# Per-request track stores (will be created per processing session)
# In a multi-worker setup, consider using Redis or database-backed track storage
_track_stores: dict[str, TrackStore] = {}

def _get_track_store(session_id: str = "default") -> TrackStore:
    """Get or create a track store for a processing session."""
    if session_id not in _track_stores:
        _track_stores[session_id] = TrackStore(window_size=5)
    return _track_stores[session_id]

def process_point(db: Session, p: AisPoint, session_id: str = "default") -> list[dict]:
    """
    - Update latest vessel position
    - Run detectors using last track points
    - Persist alerts
    
    Args:
        db: Database session
        p: AIS point to process
        session_id: Identifier for the processing session (for track store isolation)
    
    Returns list of new alerts (as dicts) generated from this point.
    """
    try:
        track_store = _get_track_store(session_id)
        tw = track_store.push(p)
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
                        # Check cooldown in database (prevent spam)
                        cooldown = db.query(AlertCooldown).filter(
                            AlertCooldown.mmsi == p2.mmsi,
                            AlertCooldown.rule_type == res["type"]
                        ).first()
                        
                        if cooldown:
                            time_since_last = (p2.timestamp - cooldown.last_alert_timestamp).total_seconds()
                            if time_since_last < settings.alert_cooldown_sec:
                                log.debug("Alert %s for MMSI %s in cooldown (%.1f s < %d s)", 
                                         res["type"], p2.mmsi, time_since_last, settings.alert_cooldown_sec)
                                continue
                            # Update existing cooldown
                            cooldown.last_alert_timestamp = p2.timestamp
                        else:
                            # Create new cooldown record
                            cooldown = AlertCooldown(
                                mmsi=p2.mmsi,
                                rule_type=res["type"],
                                last_alert_timestamp=p2.timestamp
                            )
                            db.add(cooldown)
                        
                        # Reduce evidence bloat - store only essential fields
                        evidence = res.get("evidence", {})
                        if isinstance(evidence, dict):
                            # Extract only key metrics, not full point objects
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
                            # Add any other rule-specific fields
                            for key in ["reason", "sog_diff", "implied_speed", "heading_delta", "cog_delta"]:
                                if key in evidence:
                                    slim_evidence[key] = evidence[key]
                        else:
                            slim_evidence = evidence
                        
                        log.info("Alert triggered: %s for MMSI %s - %s", res["type"], p2.mmsi, res["summary"])
                        a = Alert(
                            timestamp=p2.timestamp,
                            mmsi=p2.mmsi,
                            type=res["type"],
                            severity=int(res["severity"]),
                            summary=res["summary"],
                            evidence=slim_evidence,
                        )
                        db.add(a)
                        new_alerts.append(
                            {
                                "timestamp": p2.timestamp.isoformat(),
                                "mmsi": p2.mmsi,
                                "type": res["type"],
                                "severity": int(res["severity"]),
                                "summary": res["summary"],
                                "evidence": slim_evidence,
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
