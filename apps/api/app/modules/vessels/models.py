from sqlalchemy import (
    Column,
    String,
    Float,
    DateTime,
    Index,
    Integer,
    Boolean,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from app.core.database import Base

class VesselLatest(Base):
    __tablename__ = "vessels_latest"

    mmsi = Column(String, primary_key=True)
    organisation_id = Column(
        Integer,
        ForeignKey("organisations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        server_default="1",
    )
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
    organisation_id = Column(
        Integer,
        ForeignKey("organisations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        server_default="1",
    )
    mmsi = Column(String, index=True, nullable=False)
    timestamp = Column(DateTime, index=True, nullable=False)
    
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    
    sog = Column(Float, nullable=True)
    cog = Column(Float, nullable=True)
    heading = Column(Float, nullable=True)

Index("idx_vessel_positions_mmsi_time", VesselPosition.mmsi, VesselPosition.timestamp)
Index("idx_vessel_positions_org_mmsi_time", VesselPosition.organisation_id, VesselPosition.mmsi, VesselPosition.timestamp)
Index("idx_vessel_positions_timestamp", VesselPosition.timestamp)
Index("idx_vessels_timestamp", VesselLatest.timestamp)
Index("idx_vessels_org_mmsi", VesselLatest.organisation_id, VesselLatest.mmsi)
Index("idx_vessels_severity", VesselLatest.last_alert_severity)


class WatchlistEntry(Base):
    """Analyst-flagged MMSI for priority monitoring."""

    __tablename__ = "watchlist_entries"
    __table_args__ = (
        UniqueConstraint("organisation_id", "mmsi", name="uq_watchlist_entries_org_mmsi"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    organisation_id = Column(
        Integer,
        ForeignKey("organisations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    mmsi = Column(String, nullable=False, index=True)
    label = Column(String, nullable=False, default="")
    priority = Column(String, nullable=False, default="medium")  # low | medium | high
    added_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
