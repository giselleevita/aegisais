from sqlalchemy import Column, String, Float, DateTime, Index, Integer
from app.core.database import Base

class VesselLatest(Base):
    __tablename__ = "vessels_latest"

    mmsi = Column(String, primary_key=True)
    timestamp = Column(DateTime, index=True, nullable=False)

    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)

    sog = Column(Float, nullable=True)     # knots
    cog = Column(Float, nullable=True)     # degrees
    heading = Column(Float, nullable=True) # degrees

    last_alert_severity = Column(Integer, nullable=False, default=0)

class VesselPosition(Base):
    """Historical vessel positions for track visualization."""
    __tablename__ = "vessel_positions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    mmsi = Column(String, index=True, nullable=False)
    timestamp = Column(DateTime, index=True, nullable=False)
    
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    
    sog = Column(Float, nullable=True)
    cog = Column(Float, nullable=True)
    heading = Column(Float, nullable=True)

Index("idx_vessel_positions_mmsi_time", VesselPosition.mmsi, VesselPosition.timestamp)
Index("idx_vessel_positions_timestamp", VesselPosition.timestamp)
Index("idx_vessels_timestamp", VesselLatest.timestamp)
Index("idx_vessels_severity", VesselLatest.last_alert_severity)
