from datetime import datetime
from pydantic import BaseModel, Field
from typing import Any, Optional

class VesselLatestOut(BaseModel):
    mmsi: str
    timestamp: datetime
    lat: float
    lon: float
    sog: Optional[float] = None
    cog: Optional[float] = None
    heading: Optional[float] = None
    last_alert_severity: int = 0

class AlertOut(BaseModel):
    id: int
    timestamp: datetime
    mmsi: str
    type: str
    severity: int
    summary: str
    evidence: Any
    status: str = "new"  # new, reviewed, resolved, false_positive
    notes: Optional[str] = None

class AlertStatusUpdate(BaseModel):
    status: str = Field(..., description="Alert status: new, reviewed, resolved, false_positive")
    notes: Optional[str] = Field(None, description="Optional notes/comments")

class VesselPositionOut(BaseModel):
    id: int
    mmsi: str
    timestamp: datetime
    lat: float
    lon: float
    sog: Optional[float] = None
    cog: Optional[float] = None
    heading: Optional[float] = None

class ReplayStartIn(BaseModel):
    path: str = Field(..., description="Path to CSV file (server-side, supports .csv and .zst compressed)")
    speedup: float = Field(100.0, ge=0.1, description="Replay speed factor")
