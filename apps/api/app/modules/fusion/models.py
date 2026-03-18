from sqlalchemy import Column, String, Float, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.core.database import Base

class FusedVessel(Base):
    """
    Canonical vessel profile resolving identities across multiple sensor sources.
    This is the core entity for NATO-aligned maritime intelligence.
    """
    __tablename__ = "fused_vessels"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Core Identifiers
    mmsi = Column(String(9), unique=True, index=True, nullable=True)
    imo_number = Column(String(20), unique=True, index=True, nullable=True)
    call_sign = Column(String(20), index=True, nullable=True)
    
    # Metadata
    resolved_name = Column(String, index=True, nullable=True)
    vessel_type = Column(String, index=True, nullable=True)
    flag_state = Column(String, index=True, nullable=True)
    
    # State & Confidence
    confidence_score = Column(Float, default=1.0, nullable=False)
    
    # Lineage
    first_seen = Column(DateTime, nullable=False)
    last_updated = Column(DateTime, nullable=False)

# Composite and descriptive indexes
Index("idx_fused_vessels_identifiers", FusedVessel.mmsi, FusedVessel.imo_number)
