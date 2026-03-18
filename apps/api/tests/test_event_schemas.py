from datetime import datetime, timezone
from uuid import UUID
from app.core.events import SensorObservation, SensorType

def test_sensor_observation_valid_ais():
    """Verify that a valid AIS observation can be created."""
    data = {
        "source_id": "test_source",
        "timestamp": datetime.now(timezone.utc),
        "sensor_type": SensorType.AIS,
        "payload": {
            "mmsi": "123456789",
            "lat": 40.0,
            "lon": -74.0
        }
    }
    obs = SensorObservation(**data)
    assert isinstance(obs.id, UUID)
    assert obs.source_id == "test_source"
    assert obs.sensor_type == SensorType.AIS
    assert obs.payload["mmsi"] == "123456789"

def test_sensor_observation_invalid_priority():
    """Verify that invalid priority values raise validation errors."""
    import pytest
    from pydantic import ValidationError
    
    data = {
        "source_id": "test_source",
        "timestamp": datetime.now(timezone.utc),
        "sensor_type": SensorType.SAR,
        "payload": {"det": "sar_01"},
        "priority": 150  # Over max 100
    }
    with pytest.raises(ValidationError):
        SensorObservation(**data)

def test_sensor_observation_default_values():
    """Verify that default values are correctly populated."""
    ts = datetime.now(timezone.utc)
    obs = SensorObservation(
        source_id="test_source",
        timestamp=ts,
        sensor_type=SensorType.REGISTRY,
        payload={"vessel_name": "Aegis One"}
    )
    assert obs.priority == 0
    assert obs.received_at >= ts
    assert isinstance(obs.received_at, datetime)
