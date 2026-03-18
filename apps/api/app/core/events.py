from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, ConfigDict

class SensorType(str, Enum):
    AIS = "ais"
    SAR = "sar"
    REGISTRY = "registry"
    SANCTIONS = "sanctions"
    ENVIRONMENTAL = "environmental"

class SensorObservation(BaseModel):
    """
    Canonical event model for all incoming sensor data.
    Ensures a standardized contract for the Fusion Engine.
    """
    id: UUID = Field(default_factory=uuid4, description="Unique identifier for this observation")
    source_id: str = Field(..., description="ID of the source sensor or receptor")
    timestamp: datetime = Field(..., description="Original timestamp of the observation (UTC)")
    sensor_type: SensorType = Field(..., description="Type of sensor that produced this data")
    
    # Generic payload for source-specific data
    payload: Dict[str, Any] = Field(..., description="Raw or normalized attribute data from the source")
    
    # Optional metadata for orchestration and prioritization
    priority: int = Field(default=0, ge=0, le=100, description="Processing priority (0=low, 100=high)")
    received_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="When the system received this observation")
    
    model_config = ConfigDict(
        json_schema_extra = {
            "example": {
                "source_id": "ais_receiver_alpha",
                "timestamp": "2024-03-16T10:00:00Z",
                "sensor_type": "ais",
                "payload": {
                    "mmsi": "123456789",
                    "lat": 51.5074,
                    "lon": -0.1278,
                    "sog": 12.5
                }
            }
        }
    )
