from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Index
from .db import Base

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

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, index=True, nullable=False)
    mmsi = Column(String, index=True, nullable=False)

    type = Column(String, index=True, nullable=False)
    severity = Column(Integer, index=True, nullable=False)

    summary = Column(String, nullable=False)
    evidence = Column(JSON, nullable=False)

Index("idx_alerts_mmsi_time", Alert.mmsi, Alert.timestamp)
Index("idx_alerts_timestamp", Alert.timestamp)
Index("idx_alerts_severity", Alert.severity)
Index("idx_vessels_timestamp", VesselLatest.timestamp)
