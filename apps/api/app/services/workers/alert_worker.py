import structlog
import signal
import sys
from datetime import datetime
from typing import Any, Dict
from prometheus_client import start_http_server, Gauge, Counter
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.logging import configure_logging
from app.infrastructure.messaging.consumer import RedisConsumer
from app.modules.alerts.models import Alert, derive_alert_idempotency_key, derive_evidence_hash
from app.modules.audit.services import AuditService
from app.modules.incidents.service import create_incident_from_alert_with_flag
from app.services.workers.heartbeat import WorkerHeartbeat

log = structlog.get_logger("aegisais.worker.alerts")

HEARTBEAT = WorkerHeartbeat("/tmp/worker_alert_heartbeat")

# Metrics definitions
ALERTS_PERSISTED = Counter('aegisais_alerts_persisted_total', 'Total alerts persisted to DB')
ALERT_ERROR = Counter('aegisais_alert_processing_errors_total', 'Total errors in alert processing')
STREAM_LAG = Gauge('aegisais_stream_lag_alert', 'Redis Stream Lag (pending messages)', ['stream'])
INCIDENTS_CREATED = Counter('aegisais_incidents_created_total', 'Total incidents created from alerts')
INCIDENT_CREATE_ERRORS = Counter('aegisais_incident_create_errors_total', 'Total incident creation errors')
ALERTS_DEDUPLICATED = Counter('aegisais_alerts_deduplicated_total', 'Alerts suppressed by idempotency key')

try:
    from opentelemetry import trace  # type: ignore[import-not-found]
    _tracer = trace.get_tracer("aegisais.worker.alerts")
except Exception:  # pragma: no cover - optional dependency
    _tracer = None


def _get_existing_by_idempotency_key(db, key: str) -> Alert | None:
    return db.query(Alert).filter(Alert.idempotency_key == key).first()


def handle_alert(msg_id: str, data: Dict[str, Any]):
    """
    Process a single alert from the stream.
    Persists to DB using constraint-backed idempotency (BL-003).

    Deduplication strategy
    ----------------------
    1. Derive a canonical idempotency_key from (org_id, mmsi, type, minute-bucket UTC).
    2. Optimistic pre-check: if the key already exists, short-circuit immediately.
    3. Attempt INSERT inside a savepoint.
    4. On IntegrityError (concurrent duplicate), recover by re-querying the
       already-committed row — same pattern as incident creation.

    This means the same alert delivered multiple times from the Redis Stream is
    fully idempotent even under concurrent workers.
    """
    span_ctx = _tracer.start_as_current_span("handle_alert") if _tracer else None
    try:
        if span_ctx:
            span_ctx.__enter__()
        try:
            with SessionLocal() as db:
                ts = datetime.fromisoformat(data["timestamp"])
                org_id = settings.default_organisation_id

                idem_key = derive_alert_idempotency_key(
                    organisation_id=org_id,
                    mmsi=data["mmsi"],
                    alert_type=data["type"],
                    timestamp=ts,
                )

                # Optimistic pre-check (avoids savepoint overhead on common case)
                existing = _get_existing_by_idempotency_key(db, idem_key)
                if existing is not None:
                    ALERTS_DEDUPLICATED.inc()
                    log.info(
                        "alert_deduplicated",
                        mmsi=data["mmsi"],
                        alert_type=data["type"],
                        msg_id=msg_id,
                        alert_id=existing.id,
                        idempotency_key=idem_key,
                    )
                    return

                # Savepoint-based optimistic insert — handles concurrent workers
                try:
                    with db.begin_nested():
                        a = Alert(
                            organisation_id=org_id,
                            timestamp=ts,
                            mmsi=data["mmsi"],
                            type=data["type"],
                            severity=int(data["severity"]),
                            summary=data["summary"],
                            evidence=data["evidence"],
                            evidence_hash=data.get("evidence_hash") or derive_evidence_hash(data["evidence"]),  # BL-009
                            idempotency_key=idem_key,
                        )
                        db.add(a)
                        db.flush()
                except IntegrityError:
                    existing = _get_existing_by_idempotency_key(db, idem_key)
                    if existing is None:
                        raise
                    ALERTS_DEDUPLICATED.inc()
                    log.info(
                        "alert_deduplicated_on_conflict",
                        mmsi=data["mmsi"],
                        alert_type=data["type"],
                        msg_id=msg_id,
                        alert_id=existing.id,
                        idempotency_key=idem_key,
                    )
                    return

                incident_created = False
                try:
                    _, incident_created = create_incident_from_alert_with_flag(db, a)
                    if incident_created:
                        AuditService.log_event(
                            db,
                            action="incident.create.system",
                            change_summary="Incident auto-created from alert by worker",
                            organisation_id=int(a.organisation_id),
                            user_id="system:alert_worker",
                            resource_id=str(a.id),
                            resource_type="incident",
                            details={
                                "alert_id": a.id,
                                "mmsi": a.mmsi,
                                "alert_type": a.type,
                            },
                            correlation_id=msg_id,
                        )
                except Exception:
                    INCIDENT_CREATE_ERRORS.inc()
                    raise
                db.commit()
                ALERTS_PERSISTED.inc()
                if incident_created:
                    INCIDENTS_CREATED.inc()
                log.info("alert_persisted",
                         mmsi=data["mmsi"],
                         alert_type=data["type"],
                         msg_id=msg_id,
                         idempotency_key=idem_key)
        except Exception as e:
            ALERT_ERROR.inc()
            raise e
    except Exception as e:
        log.error("alert_processing_error", msg_id=msg_id, error=str(e), exc_info=True)
    finally:
        if span_ctx:
            span_ctx.__exit__(None, None, None)

def main():
    configure_logging()
    
    log.info("starting_alert_worker", mode="persistence", metrics_port=9002)
    start_http_server(9002)
    
    consumer = RedisConsumer(
        stream_name=settings.stream_ais_alerts,
        group_name="alert_group",
        consumer_name="worker_1"
    )
    
    def shutdown_handler(sig, frame):
        log.info("shutting_down")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)
    
    def on_tick():
        STREAM_LAG.labels(stream=settings.stream_ais_alerts).set(consumer.get_lag())
        HEARTBEAT.on_loop_tick()

    try:
        consumer.listen(callback=handle_alert, on_tick=on_tick)
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
