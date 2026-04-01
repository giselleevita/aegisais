import structlog
import signal
import sys
import time
from datetime import datetime
from typing import Any, Dict, List
from prometheus_client import start_http_server, Gauge, Summary, Counter

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.logging import configure_logging
from app.infrastructure.messaging.consumer import RedisConsumer
from app.modules.vessels.models import VesselLatest, VesselPosition
from app.services.workers.heartbeat import WorkerHeartbeat

log = structlog.get_logger("aegisais.worker.persistence")

HEARTBEAT = WorkerHeartbeat("/tmp/worker_persistence_heartbeat")

# Metrics definitions
FLUSH_LATENCY = Summary('aegisais_persistence_flush_latency_seconds', 'Time spent flushing batch to DB')
FLUSH_BATCH_SIZE = Summary('aegisais_persistence_batch_size', 'Number of items in flushed batch')
PERSISTENCE_ERRORS = Counter('aegisais_persistence_errors_total', 'Total persistence errors')
STREAM_LAG = Gauge('aegisais_stream_lag_persistence', 'Redis Stream Lag (pending messages)', ['stream'])

class PersistenceWorker:
    def __init__(self):
        self.batch: List[Dict[str, Any]] = []
        self.last_flush = time.time()
        self.consumer = RedisConsumer(
            stream_name=settings.stream_ais_processed,
            group_name="persistence_group",
            consumer_name="worker_1"
        )

    def handle_message(self, msg_id: str, data: Dict[str, Any]):
        """
        Add message to batch. Flush if batch is full.
        """
        self.batch.append(data)
        HEARTBEAT.on_successful_message()

        if len(self.batch) >= settings.persistence_batch_size:
            self.flush()
        elif time.time() - self.last_flush > settings.persistence_flush_interval_sec:
            self.flush()

    def flush(self):
        """
        Persist the current batch to the database.
        """
        if not self.batch:
            self.last_flush = time.time()
            return

        batch_size = len(self.batch)
        FLUSH_BATCH_SIZE.observe(batch_size)
        
        with FLUSH_LATENCY.time():
            try:
                with SessionLocal() as db:
                    for data in self.batch:
                        ts = datetime.fromisoformat(data["timestamp"])
                        mmsi = data["mmsi"]
                        org_id = int(data.get("organisation_id") or settings.default_organisation_id)
                        
                        # Update Latest
                        v = (
                            db.query(VesselLatest)
                            .filter(
                                VesselLatest.mmsi == mmsi,
                                VesselLatest.organisation_id == org_id,
                            )
                            .first()
                        )
                        if not v:
                            v = VesselLatest(
                                mmsi=mmsi,
                                organisation_id=org_id,
                                timestamp=ts,
                                lat=float(data["lat"]),
                                lon=float(data["lon"]),
                                sog=float(data["sog"]),
                                cog=float(data["cog"]),
                                heading=float(data["heading"]),
                                last_alert_severity=int(data["last_alert_severity"])
                            )
                            db.add(v)
                        else:
                            if ts >= v.timestamp:
                                v.timestamp = ts
                                v.lat = float(data["lat"])
                                v.lon = float(data["lon"])
                                v.sog = float(data["sog"])
                                v.cog = float(data["cog"])
                                v.heading = float(data["heading"])
                                v.last_alert_severity = max(v.last_alert_severity or 0, int(data["last_alert_severity"]))

                        # Insert historical position
                        pos = VesselPosition(
                            organisation_id=org_id,
                            mmsi=mmsi,
                            timestamp=ts,
                            lat=float(data["lat"]),
                            lon=float(data["lon"]),
                            sog=float(data["sog"]),
                            cog=float(data["cog"]),
                            heading=float(data["heading"])
                        )
                        db.add(pos)
                    
                    db.commit()
                
                log.info("flushed_batch", count=batch_size)
                HEARTBEAT.on_successful_message()
                self.batch = []
                self.last_flush = time.time()
                
            except Exception as e:
                PERSISTENCE_ERRORS.inc()
                log.error("flush_error", error=str(e), exc_info=True)
                self.batch = []
                self.last_flush = time.time()

    def run(self):
        log.info("starting_persistence_worker")
        try:
            def on_tick():
                STREAM_LAG.labels(stream=settings.stream_ais_processed).set(
                    self.consumer.get_lag()
                )
                HEARTBEAT.on_loop_tick()

            self.consumer.listen(callback=self.handle_message, on_tick=on_tick)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        log.info("shutting_down")
        self.flush()  # Final flush
        sys.exit(0)

def main():
    configure_logging()
    
    log.info("starting_persistence_worker", metrics_port=9001)
    start_http_server(9001)
    
    worker = PersistenceWorker()
    
    def shutdown_handler(sig, frame):
        worker.stop()
        
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)
    
    worker.run()

if __name__ == "__main__":
    main()
