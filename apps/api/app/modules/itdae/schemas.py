from pydantic import BaseModel, Field, ConfigDict
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


class GeofenceZoneCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    risk_level: str = Field(..., description="low | medium | high | critical")
    polygon_geojson: dict[str, Any] = Field(..., description="GeoJSON Polygon geometry")


class GeofenceZoneUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    risk_level: Optional[str] = None
    polygon_geojson: Optional[dict[str, Any]] = None
    is_active: Optional[bool] = None


class GeofenceZoneOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: Optional[str] = None
    risk_level: str
    polygon_geojson: dict[str, Any]
    is_active: bool
    created_by_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
