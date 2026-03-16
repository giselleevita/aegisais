from sqlalchemy import Column, Integer, String, DateTime, JSON, Index
from app.core.database import Base

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

# Composite indexes
Index("idx_alerts_mmsi_time", Alert.mmsi, Alert.timestamp)
Index("idx_alerts_type_time", Alert.type, Alert.timestamp)
Index("idx_alerts_severity_time", Alert.severity, Alert.timestamp)
Index("idx_alerts_timestamp", Alert.timestamp)
Index("idx_alerts_severity", Alert.severity)
Index("idx_cooldown_mmsi_type", AlertCooldown.mmsi, AlertCooldown.rule_type)
Index("idx_cooldown_timestamp", AlertCooldown.last_alert_timestamp)
