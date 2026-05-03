import structlog
import signal
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, List
from prometheus_client import start_http_server, Gauge, Counter, Histogram

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.logging import configure_logging
from app.services.workers.heartbeat import WorkerHeartbeat
from app.modules.vessels.models import VesselLatest, VesselPosition
from app.infrastructure.providers.sais_client import SAISClientFactory
from app.detection.spoofing import detect_multi_source_vessel_identity_conflict
from app.modules.alerts.models import Alert

log = structlog.get_logger("aegisais.worker.sais_fetch")

HEARTBEAT = WorkerHeartbeat("/tmp/worker_sais_fetch_heartbeat")

# Metrics definitions
SAIS_POSITIONS_FETCHED = Counter(
    'sais_positions_fetched_total',
    'Total positions fetched from S-AIS provider',
    ['provider']
)
SAIS_FETCH_ERRORS = Counter(
    'sais_fetch_errors_total',
    'Total errors during S-AIS fetch',
    ['provider', 'error_type']
)
SAIS_FETCH_LATENCY = Histogram(
    'sais_fetch_latency_seconds',
    'Time taken to fetch positions from S-AIS provider',
    ['provider'],
    buckets=(0.5, 1.0, 2.5, 5.0, 10.0)
)
SAIS_MMSIS_ACTIVE = Gauge(
    'sais_mmsis_active',
    'Number of active MMSIs tracked via S-AIS',
    ['provider']
)

# Signal handling for graceful shutdown
shutdown_event = False


def handle_sigterm(signum, frame):
    global shutdown_event
    shutdown_event = True
    log.info("SIGTERM received, initiating graceful shutdown")
    sys.exit(0)


def fetch_active_mmsis(db) -> List[int]:
    """Fetch all active MMSIs from vessels_latest table."""
    try:
        vessels = db.query(VesselLatest.mmsi).distinct().all()
        return [v[0] for v in vessels if v[0]]
    except Exception as e:
        log.error("error_fetching_mmsis", error=str(e))
        SAIS_FETCH_ERRORS.labels(provider=settings.SAIS_PROVIDER, error_type="query_error").inc()
        return []


def store_sais_position(db, mmsi: int, lat: float, lon: float,
                       organisation_id: int = 1, confidence: float = 1.0):
    """Store S-AIS position in both vessel_positions (history) and vessels_latest (current)."""
    try:
        now = datetime.now(timezone.utc)

        # Store in vessel_positions (historical)
        position = VesselPosition(
            mmsi=mmsi,
            lat=lat,
            lon=lon,
            timestamp=now,
            organisation_id=organisation_id,
            source='sais'
        )
        db.add(position)

        # Update or create in vessels_latest (current)
        latest = db.query(VesselLatest).filter_by(mmsi=mmsi).first()
        if latest:
            latest.lat = lat
            latest.lon = lon
            latest.updated_at = now
            latest.source = 'sais'
            latest.confidence = confidence
            latest.provenance = ['sais']
        else:
            latest = VesselLatest(
                mmsi=mmsi,
                lat=lat,
                lon=lon,
                organisation_id=organisation_id,
                source='sais',
                confidence=confidence,
                provenance=['sais'],
                updated_at=now
            )
            db.add(latest)

        db.commit()
        log.debug("sais_position_stored", mmsi=mmsi, lat=lat, lon=lon)
        SAIS_POSITIONS_FETCHED.labels(provider=settings.SAIS_PROVIDER).inc()

        # Check for multi-source spoofing conflicts
        check_and_alert_spoofing(db, mmsi, organisation_id)
        return True

    except Exception as e:
        db.rollback()
        log.error("error_storing_position", mmsi=mmsi, error=str(e))
        SAIS_FETCH_ERRORS.labels(provider=settings.SAIS_PROVIDER, error_type="store_error").inc()
        return False


def fetch_sais_positions() -> List[Dict[str, Any]]:
    """Fetch positions from S-AIS provider."""
    try:
        client = SAISClientFactory.get_client(settings.SAIS_PROVIDER)
        if not client:
            log.warning("sais_provider_unavailable", provider=settings.SAIS_PROVIDER)
            return []

        start_time = time.time()
        positions = client.get_all_positions()
        elapsed = time.time() - start_time

        SAIS_FETCH_LATENCY.labels(provider=settings.SAIS_PROVIDER).observe(elapsed)
        log.info("sais_positions_fetched", count=len(positions), latency=elapsed)

        return positions

    except Exception as e:
        log.error("sais_fetch_failed", error=str(e))
        SAIS_FETCH_ERRORS.labels(provider=settings.SAIS_PROVIDER, error_type="fetch_error").inc()
        return []


def run_fetch_cycle():
    """Run a single 5-minute fetch cycle."""
    db = SessionLocal()
    try:
        log.info("sais_cycle_start")

        # Get all active MMSIs
        mmsis = fetch_active_mmsis(db)
        log.info("mmsis_to_fetch", count=len(mmsis))

        if not mmsis:
            log.warning("no_active_mmsis")
            SAIS_MMSIS_ACTIVE.labels(provider=settings.SAIS_PROVIDER).set(0)
            return

        # Fetch positions from provider
        positions = fetch_sais_positions()

        if not positions:
            log.warning("no_positions_returned")
            return

        # Store positions that match our tracked MMSIs
        stored_count = 0
        for pos in positions:
            mmsi = pos.get('mmsi')
            if mmsi in mmsis:
                if store_sais_position(
                    db,
                    mmsi=mmsi,
                    lat=pos.get('lat'),
                    lon=pos.get('lon'),
                    confidence=pos.get('confidence', 1.0)
                ):
                    stored_count += 1

        SAIS_MMSIS_ACTIVE.labels(provider=settings.SAIS_PROVIDER).set(len(mmsis))
        log.info("sais_cycle_complete", fetched=len(positions), stored=stored_count)
        HEARTBEAT.update()

    except Exception as e:
        log.error("sais_cycle_failed", error=str(e))
        SAIS_FETCH_ERRORS.labels(provider=settings.SAIS_PROVIDER, error_type="cycle_error").inc()
    finally:
        db.close()




def check_and_alert_spoofing(db, mmsi: int, organisation_id: int = 1):
    """Check for multi-source identity conflicts and create alerts."""
    try:
        # Fetch recent positions from both sources for this MMSI
        latest = db.query(VesselLatest).filter_by(mmsi=mmsi).first()
        if not latest:
            return

        # Build a sources dict with positions from different sources
        recent_positions = db.query(VesselPosition).filter_by(mmsi=mmsi).order_by(
            VesselPosition.timestamp.desc()
        ).limit(10).all()

        if not recent_positions:
            return

        sources = {}
        for pos in recent_positions:
            source_key = pos.source or 'unknown'
            if source_key not in sources:
                sources[source_key] = {
                    'lat': pos.lat,
                    'lon': pos.lon,
                    'timestamp': pos.timestamp
                }

        # Check for spoofing conflicts
        alert_dict = detect_multi_source_vessel_identity_conflict(mmsi, sources)
        if alert_dict:
            alert = Alert(
                organisation_id=organisation_id,
                mmsi=mmsi,
                type=alert_dict['type'],
                severity=alert_dict['severity'],
                summary=alert_dict['summary'],
                evidence=alert_dict['evidence'],
                source='sais'
            )
            db.add(alert)
            db.commit()
            log.info("spoofing_alert_created", mmsi=mmsi, severity=alert_dict['severity'])

    except Exception as e:
        log.error("spoofing_check_failed", mmsi=mmsi, error=str(e))


def main():
    configure_logging()
    signal.signal(signal.SIGTERM, handle_sigterm)

    log.info("sais_fetch_worker_starting", provider=settings.SAIS_PROVIDER)

    # Start Prometheus metrics server on port 8002
    start_http_server(8002)

    # Initial heartbeat
    HEARTBEAT.update()

    # Fetch cycle every 5 minutes
    FETCH_INTERVAL = 300

    while not shutdown_event:
        try:
            run_fetch_cycle()
        except Exception as e:
            log.error("worker_error", error=str(e))
            SAIS_FETCH_ERRORS.labels(provider=settings.SAIS_PROVIDER, error_type="unknown").inc()

        time.sleep(FETCH_INTERVAL)


if __name__ == "__main__":
    main()
