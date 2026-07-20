"""Regression tests for failures that only appear in isolated worker processes."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from uuid import UUID

import pytest

from app.infrastructure.messaging.publisher import RedisPublisher
from app.modules.auth.models import Organisation
from app.modules.vessels.models import VesselLatest, VesselPosition
from tests.conftest import TestingSessionLocal


def test_redis_publisher_serializes_rule_timestamps_and_ids() -> None:
    published: dict[str, object] = {}

    class FakeRedis:
        def xadd(self, stream: str, fields: dict[str, str]) -> None:
            published.update({"stream": stream, "fields": fields})

    sender = RedisPublisher()
    sender.redis = FakeRedis()
    sender.publish(
        "alerts",
        {
            "timestamp": datetime(2026, 8, 20, 9, 0, tzinfo=timezone.utc),
            "event_id": UUID("00000000-0000-0000-0000-000000000001"),
        },
    )

    payload = json.loads(published["fields"]["payload"])  # type: ignore[index]
    assert payload == {
        "timestamp": "2026-08-20T09:00:00+00:00",
        "event_id": "00000000-0000-0000-0000-000000000001",
    }


@pytest.mark.parametrize(
    ("worker_module", "required_tables"),
    [
        ("app.services.workers.persistence_worker", {"organisations", "vessels_latest"}),
        ("app.services.workers.observation_worker", {"organisations", "observations", "fusion_events"}),
        (
            "app.services.workers.alert_worker",
            {"organisations", "assets", "iot_devices", "fusion_events", "alerts"},
        ),
    ],
)
def test_worker_import_registers_all_foreign_key_targets(
    worker_module: str,
    required_tables: set[str],
) -> None:
    code = (
        f"import {worker_module}; "
        "from app.core.database import Base; "
        f"required={required_tables!r}; "
        "missing=required-set(Base.metadata.tables); "
        "assert not missing, missing"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_persistence_worker_accepts_aware_replay_time_against_naive_legacy_row(
    client, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.services.workers import persistence_worker as module

    with TestingSessionLocal() as setup:
        setup.add(Organisation(id=41, name="Festival persistence test", slug="festival-persistence-test"))
        setup.add(
            VesselLatest(
                organisation_id=41,
                mmsi="273000002",
                timestamp=datetime(2026, 8, 20, 9, 0),
                lat=54.0,
                lon=12.0,
                updated_at=datetime(2026, 8, 20, 9, 0, tzinfo=timezone.utc),
            )
        )
        setup.commit()

    monkeypatch.setattr(module, "SessionLocal", TestingSessionLocal)
    worker = module.PersistenceWorker.__new__(module.PersistenceWorker)
    worker.batch = [
        {
            "organisation_id": 41,
            "mmsi": "273000002",
            "timestamp": "2026-08-20T09:05:00+00:00",
            "lat": 54.1,
            "lon": 12.1,
            "source": "festival-replay",
        },
        {
            "organisation_id": 41,
            "mmsi": "273000002",
            "timestamp": "2026-08-20T09:10:00+00:00",
            "lat": 54.2,
            "lon": 12.2,
            "source": "festival-replay",
        },
    ]
    worker.last_flush = 0.0

    worker.flush()

    with TestingSessionLocal() as verify:
        latest = verify.query(VesselLatest).filter_by(organisation_id=41, mmsi="273000002").one()
        positions = verify.query(VesselPosition).filter_by(organisation_id=41, mmsi="273000002").all()
        assert latest.timestamp == datetime(2026, 8, 20, 9, 10)
        assert latest.lat == 54.2
        assert len(positions) == 2
    assert worker.batch == []


def test_persistence_worker_flushes_partial_batch_on_tick(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.workers import persistence_worker as module

    worker = module.PersistenceWorker.__new__(module.PersistenceWorker)
    worker.batch = [{"mmsi": "273000002"}]
    worker.last_flush = 0.0
    worker.consumer = type("Consumer", (), {"get_lag": lambda self: 0})()
    flushed: list[bool] = []
    worker.flush = lambda: flushed.append(True)  # type: ignore[method-assign]
    monkeypatch.setattr(module.time, "time", lambda: module.settings.persistence_flush_interval_sec + 1)

    worker.on_tick()

    assert flushed == [True]
