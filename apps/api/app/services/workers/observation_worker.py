"""Persist canonical observations and emit explainable fusion alerts."""

from __future__ import annotations

import signal
import sys
from typing import Any

import structlog
from prometheus_client import Counter, Gauge, start_http_server

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.logging import configure_logging
from app.infrastructure.messaging.consumer import RedisConsumer
from app.infrastructure.messaging.publisher import publisher
from app.modules.auth.models import Organisation  # noqa: F401 - registers FK target in worker metadata
from app.modules.fusion.observation_fusion import event_to_alert, fuse_observation, scan_stale_ais_near_cables
from app.modules.observations.contracts import CanonicalObservation
from app.modules.observations.service import persist_observation
from app.services.workers.heartbeat import WorkerHeartbeat

log = structlog.get_logger("aegisais.worker.observations")
HEARTBEAT = WorkerHeartbeat("/tmp/worker_observation_heartbeat")
OBSERVATIONS_PERSISTED = Counter("aegisais_observations_persisted_total", "Canonical observations persisted", ["layer"])
OBSERVATIONS_DEDUPLICATED = Counter("aegisais_observations_deduplicated_total", "Duplicate observations ignored", ["layer"])
FUSION_EVENTS = Counter("aegisais_fusion_events_total", "Fusion events emitted", ["event_type", "severity"])
STREAM_LAG = Gauge("aegisais_observation_stream_lag", "Canonical observation stream lag")


def handle_observation(msg_id: str, data: dict[str, Any]) -> None:
    try:
        observation = CanonicalObservation.model_validate(data)
        org_id = int(observation.access.ownerOrgId or settings.default_organisation_id)
        with SessionLocal() as db:
            row, created = persist_observation(db, observation, org_id)
            if not created:
                OBSERVATIONS_DEDUPLICATED.labels(layer=observation.layerId).inc()
                return
            OBSERVATIONS_PERSISTED.labels(layer=observation.layerId).inc()
            events = fuse_observation(db, row)
            db.commit()
            for event in events:
                publisher.publish(settings.stream_ais_alerts, event_to_alert(event))
                FUSION_EVENTS.labels(event_type=event.event_type, severity=event.severity).inc()
        HEARTBEAT.on_successful_message()
    except Exception as exc:
        log.error("observation_processing_failed", msg_id=msg_id, error=str(exc), exc_info=True)


def main() -> None:
    configure_logging()
    start_http_server(9004)
    consumer = RedisConsumer(
        stream_name=settings.stream_observations,
        group_name="observation_group",
        consumer_name="worker_1",
    )

    def shutdown(_sig, _frame):
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    def on_tick() -> None:
        STREAM_LAG.set(consumer.get_lag())
        try:
            with SessionLocal() as db:
                stale_events = scan_stale_ais_near_cables(
                    db,
                    organisation_id=settings.default_organisation_id,
                )
                db.commit()
                for event in stale_events:
                    publisher.publish(settings.stream_ais_alerts, event_to_alert(event))
                    FUSION_EVENTS.labels(event_type=event.event_type, severity=event.severity).inc()
        except Exception as exc:
            log.warning("ais_silence_scan_failed", error=str(exc))
        HEARTBEAT.on_loop_tick()

    consumer.listen(callback=handle_observation, on_tick=on_tick)


if __name__ == "__main__":
    main()
