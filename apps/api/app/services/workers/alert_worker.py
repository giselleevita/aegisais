import structlog
import signal
import sys
from datetime import datetime
from typing import Any, Dict
from prometheus_client import start_http_server, Gauge, Counter

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.logging import configure_logging
from app.infrastructure.messaging.consumer import RedisConsumer
from app.modules.alerts.models import Alert

log = structlog.get_logger("aegisais.worker.alerts")

# Metrics definitions
ALERTS_PERSISTED = Counter('aegisais_alerts_persisted_total', 'Total alerts persisted to DB')
ALERT_ERROR = Counter('aegisais_alert_processing_errors_total', 'Total errors in alert processing')
STREAM_LAG = Gauge('aegisais_stream_lag_alert', 'Redis Stream Lag (pending messages)', ['stream'])

def handle_alert(msg_id: str, data: Dict[str, Any]):
    """
    Process a single alert from the stream.
    Persists to DB. 
    """
    try:
        # 1. Persist to DB
        try:
            with SessionLocal() as db:
                a = Alert(
                    timestamp=datetime.fromisoformat(data["timestamp"]),
                    mmsi=data["mmsi"],
                    type=data["type"],
                    severity=int(data["severity"]),
                    summary=data["summary"],
                    evidence=data["evidence"],
                )
                db.add(a)
                db.commit()
                ALERTS_PERSISTED.inc()
                log.info("alert_persisted", 
                         mmsi=data["mmsi"], 
                         alert_type=data["type"], 
                         msg_id=msg_id)
        except Exception as e:
            ALERT_ERROR.inc()
            raise e
        
    except Exception as e:
        log.error("alert_processing_error", msg_id=msg_id, error=str(e), exc_info=True)

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
    
    try:
        consumer.listen(callback=handle_alert)
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
