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
    
    # Alert management fields
    status = Column(String, default="new", nullable=False, index=True)  # new, reviewed, resolved, false_positive
    notes = Column(String, nullable=True)  # User notes/comments

class AlertCooldown(Base):
    """Tracks last alert time per (MMSI, rule_type) for cooldown mechanism."""
    __tablename__ = "alert_cooldowns"

    mmsi = Column(String, primary_key=True, nullable=False)
    rule_type = Column(String, primary_key=True, nullable=False)
    last_alert_timestamp = Column(DateTime, nullable=False, index=True)

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

# Composite indexes for common query patterns
Index("idx_alerts_mmsi_time", Alert.mmsi, Alert.timestamp)
Index("idx_alerts_type_time", Alert.type, Alert.timestamp)  # For filtering by type and time
Index("idx_alerts_severity_time", Alert.severity, Alert.timestamp)  # For severity + time queries
Index("idx_alerts_timestamp", Alert.timestamp)
Index("idx_alerts_severity", Alert.severity)
Index("idx_vessels_timestamp", VesselLatest.timestamp)
Index("idx_vessels_severity", VesselLatest.last_alert_severity)  # For severity filtering
Index("idx_cooldown_mmsi_type", AlertCooldown.mmsi, AlertCooldown.rule_type)
Index("idx_cooldown_timestamp", AlertCooldown.last_alert_timestamp)  # For cleanup queries
