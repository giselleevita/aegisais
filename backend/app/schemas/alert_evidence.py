"""Pydantic models for alert evidence structures."""
from pydantic import BaseModel, Field
from typing import Optional

class TeleportEvidence(BaseModel):
    """Evidence structure for teleport alerts."""
    dt_sec: float = Field(..., description="Time gap in seconds")
    distance_m: float = Field(..., description="Distance in meters")
    implied_speed_kn: float = Field(..., description="Implied speed in knots")
    tier: str = Field(..., description="Time gap tier: short, medium, long_gap")
    p1_lat: float
    p1_lon: float
    p1_timestamp: str
    p2_lat: float
    p2_lon: float
    p2_timestamp: str
    p2_sog: Optional[float] = None
    p2_cog: Optional[float] = None
    p2_heading: Optional[float] = None

class TurnRateEvidence(BaseModel):
    """Evidence structure for turn rate alerts."""
    dt_sec: float
    turn_rate_deg_per_sec: float
    heading_delta: Optional[float] = None
    cog_delta: Optional[float] = None
    speed: Optional[float] = None
    tier: Optional[str] = None
    p1_lat: float
    p1_lon: float
    p1_timestamp: str
    p2_lat: float
    p2_lon: float
    p2_timestamp: str
    p2_sog: Optional[float] = None
    p2_cog: Optional[float] = None
    p2_heading: Optional[float] = None

class PositionInvalidEvidence(BaseModel):
    """Evidence structure for position invalid alerts."""
    reason: str
    p1_lat: float
    p1_lon: float
    p1_timestamp: str
    p2_lat: float
    p2_lon: float
    p2_timestamp: str

class AccelerationEvidence(BaseModel):
    """Evidence structure for acceleration alerts."""
    accel_knots_per_sec: Optional[float] = None
    sog_diff: Optional[float] = None
    implied_speed: Optional[float] = None
    p1_lat: float
    p1_lon: float
    p1_timestamp: str
    p2_lat: float
    p2_lon: float
    p2_timestamp: str
    p2_sog: Optional[float] = None
