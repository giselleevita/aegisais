from sqlalchemy import Column, Integer, String, Float, DateTime, SmallInteger, JSON, Index, Text
from app.core.database import Base

class ItdaePosition(Base):
    __tablename__ = "itdae_positions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    mmsi = Column(String(9), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    speed = Column(Float, nullable=True)
    course = Column(Float, nullable=True)
    heading = Column(Float, nullable=True)
    nav_status = Column(SmallInteger, nullable=True)
    msg_type = Column(SmallInteger, nullable=True)
    raw_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default="now()")

Index("idx_itdae_pos_mmsi_ts", ItdaePosition.mmsi, ItdaePosition.timestamp)

class ItdaeGeofenceZone(Base):
    __tablename__ = "itdae_geofence_zones"

    id = Column(String(64), primary_key=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    risk_level = Column(String(16), nullable=False)
    polygon_geojson = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default="now()")
    updated_at = Column(DateTime(timezone=True), server_default="now()")
