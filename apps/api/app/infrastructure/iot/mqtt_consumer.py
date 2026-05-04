from __future__ import annotations

from datetime import datetime
from typing import Any

from app.infrastructure.iot.telemetry_normalizer import normalize_mqtt_payload


class MqttTelemetryConsumer:
    """Canonical MQTT message adapter.

    The runtime broker integration can hand each received topic/payload pair to this
    consumer to produce the same normalized envelope used by the API ingest path.
    """

    def normalize_message(
        self,
        *,
        topic: str,
        payload: dict[str, Any] | str,
        device_id: int | None = None,
        recorded_at: datetime | None = None,
        event_id: str | None = None,
    ) -> dict[str, Any]:
        return normalize_mqtt_payload(
            topic=topic,
            payload=payload,
            device_id=device_id,
            recorded_at=recorded_at,
            event_id=event_id,
        )