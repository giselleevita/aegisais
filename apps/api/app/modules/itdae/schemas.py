from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Any

class ItdaePositionSchema(BaseModel):
    id: Optional[int] = None
    mmsi: str = Field(..., max_length=9)
    timestamp: datetime
    lat: float
    lon: float
    speed: Optional[float] = None
    course: Optional[float] = None
    heading: Optional[float] = None
    nav_status: Optional[int] = None
    msg_type: Optional[int] = None
    raw_json: Optional[Any] = None
    created_at: Optional[datetime] = None
