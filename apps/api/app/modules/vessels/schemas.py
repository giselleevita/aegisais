from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

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


WatchlistPriority = Literal["low", "medium", "high"]


class WatchlistEntryOut(BaseModel):
    id: int
    mmsi: str
    label: str
    priority: WatchlistPriority
    added_by_id: int
    created_at: datetime
    is_active: bool

    model_config = {"from_attributes": True}


class WatchlistCreate(BaseModel):
    mmsi: str = Field(..., min_length=9, max_length=9)
    label: str = Field(default="", max_length=512)
    priority: WatchlistPriority = "medium"
