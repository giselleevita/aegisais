import structlog
import signal
import sys
import time
from datetime import datetime
from typing import Any, Dict
from prometheus_client import start_http_server, Gauge, Summary, Counter

from app.core.config import settings
from app.core.logging import configure_logging
from app.infrastructure.messaging.consumer import RedisConsumer
from app.infrastructure.messaging.publisher import publisher
from app.infrastructure.ingest.loaders import AisPoint
from app.services.pipeline import process_point

log = structlog.get_logger("aegisais.worker.processing")

# Metrics definitions
STREAM_LAG = Gauge('aegisais_stream_lag', 'Redis Stream Lag (pending messages)', ['stream'])
PROCESSING_LATENCY = Summary('aegisais_processing_latency_seconds', 'Time spent processing AIS point')
ALERTS_GENERATED = Counter('aegisais_alerts_total', 'Total alerts generated', ['rule_type', 'severity'])
POSITION_PROCESSED = Counter('aegisais_positions_processed_total', 'Total AIS points processed')

@PROCESSING_LATENCY.time()
def handle_ais_point(msg_id: str, data: Dict[str, Any]):
    """
    Process a single AIS point from the raw stream.
    Publishes results to 'processed' and 'alerts' streams.
    """
    try:
        # Reconstruct AisPoint from dict
        timestamp = datetime.fromisoformat(data["timestamp"])
        p = AisPoint(
            mmsi=data["mmsi"],
            timestamp=timestamp,
            lat=float(data["lat"]),
            lon=float(data["lon"]),
            sog=float(data["sog"]),
            cog=float(data["cog"]),
            heading=float(data.get("heading", 0))
        )
        
        # Pure logic processing (no DB)
        start_time = time.time()
        result = process_point(p)
        
        # 1. Publish to processed stream for persistence
        publisher.publish(settings.stream_ais_processed, result["point"])
        
        # 2. Publish alerts to alerts stream for dispatch
        for alert in result["alerts"]:
            publisher.publish(settings.stream_ais_alerts, alert)
            ALERTS_GENERATED.labels(rule_type=alert["type"], severity=alert["severity"]).inc()
            
        POSITION_PROCESSED.inc()
        log.debug("processed_message", 
                  msg_id=msg_id, 
                  mmsi=p.mmsi, 
                  alerts_count=len(result["alerts"]),
                  duration=time.time() - start_time)
                
    except Exception as e:
        log.error("processing_error", msg_id=msg_id, error=str(e), exc_info=True)

def main():
    configure_logging()
    
    log.info("starting_worker", mode="decoupled", metrics_port=9000)
    start_http_server(9000)
    
    # Listen to the raw ingestion stream
    consumer = RedisConsumer(
        stream_name=settings.stream_ais_raw,
        group_name="processing_group",
        consumer_name="worker_1"
    )
    
    def shutdown(sig, frame):
        log.info("shutting_down")
        sys.exit(0)
        
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)
    
    try:
        consumer.listen(
            callback=handle_ais_point,
            on_tick=lambda: STREAM_LAG.labels(stream=settings.stream_ais_raw).set(consumer.get_lag())
        )
    except KeyboardInterrupt:
        shutdown(None, None)

if __name__ == "__main__":
    main()
