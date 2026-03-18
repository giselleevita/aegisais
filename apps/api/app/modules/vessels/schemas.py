from datetime import datetime
from pydantic import BaseModel
from typing import Optional

class VesselLatestOut(BaseModel):
    mmsi: str
    timestamp: datetime
    lat: float
    lon: float
    sog: Optional[float] = None
    cog: Optional[float] = None
    heading: Optional[float] = None
    last_alert_severity: int = 0

class VesselPositionOut(BaseModel):
    id: int
    mmsi: str
    timestamp: datetime
    lat: float
    lon: float
    sog: Optional[float] = None
    cog: Optional[float] = None
    heading: Optional[float] = None
