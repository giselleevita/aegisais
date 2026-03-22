"""
ITDAE processing pipeline.

Mirrors backend.app.services.pipeline but for the ITDAE module.
Called when a new ItdaePoint arrives (from aisstream.io or replay).
Runs all POINT_PAIR_RULES and WINDOW_RULES, persists alerts to DB.
"""
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.modules.itdae.tracking.features_itdae import ItdaePoint
from app.modules.itdae.tracking.track_store_itdae import ItdaeTrackStore
from app.modules.itdae.detection.rules_itdae import POINT_PAIR_RULES, WINDOW_RULES
from app.modules.alerts.models import Alert  # Reuse existing Alert table
from app.modules.vessels.watchlist_enrich import enrich_evidence_dict

log = logging.getLogger("aegisais.itdae.pipeline")

# Module-level track store (in-memory, shared per process)
_store = ItdaeTrackStore(window_size=10)


def process_itdae_point(point: ItdaePoint, db: Session) -> list[dict[str, Any]]:
    """
    Process one incoming ITDAE AIS point through the full pipeline.

    Steps:
    1. Push point to per-vessel track window
    2. Run all POINT_PAIR_RULES against (prev_point, current_point)
    3. Run all WINDOW_RULES against the full window
    4. Persist any resulting alerts to the DB (reusing Alert model)
    5. Return list of alert dicts generated

    Args:
        point: The incoming ItdaePoint
        db: SQLAlchemy session

    Returns:
        List of alert dicts generated (may be empty)
    """
    window = _store.push(point)
    alerts_generated = []

    points_list = list(window.points)
    if len(points_list) < 2:
        return []

    p1 = points_list[-2]
    p2 = points_list[-1]

    # ── Point-pair rules ──────────────────────────────────────────────────
    for rule_fn in POINT_PAIR_RULES:
        try:
            result = rule_fn(p1, p2)
            if result:
                _persist_alert(result, db)
                alerts_generated.append(result)
                log.info("ITDAE alert: type=%s severity=%d mmsi=%s",
                         result["type"], result["severity"], p2.mmsi)
        except Exception as exc:
            log.exception("Rule %s raised: %s", rule_fn.__name__, exc)

    # ── Window rules ──────────────────────────────────────────────────────
    for rule_fn in WINDOW_RULES:
        try:
            result = rule_fn(points_list)
            if result:
                _persist_alert(result, db)
                alerts_generated.append(result)
                log.info("ITDAE window alert: type=%s severity=%d mmsi=%s",
                         result["type"], result["severity"], p2.mmsi)
        except Exception as exc:
            log.exception("Window rule %s raised: %s", rule_fn.__name__, exc)

    return alerts_generated


def _persist_alert(alert: dict[str, Any], db: Session) -> None:
    """Persist an ITDAE alert into the shared alerts table."""
    try:
        raw_ev = alert.get("evidence") or {}
        mmsi = raw_ev.get("mmsi", "UNKNOWN")
        evidence = (
            enrich_evidence_dict(db, mmsi, raw_ev)
            if mmsi != "UNKNOWN"
            else (dict(raw_ev) if isinstance(raw_ev, dict) else {})
        )
        record = Alert(
            organisation_id=settings.default_organisation_id,
            timestamp=datetime.now(timezone.utc),
            mmsi=mmsi,
            type=alert["type"],
            severity=alert["severity"],
            summary=alert["summary"],
            evidence=evidence,
            status="new",
        )
        db.add(record)
        db.commit()
    except Exception as exc:
        db.rollback()
        log.exception("Failed to persist ITDAE alert: %s", exc)
