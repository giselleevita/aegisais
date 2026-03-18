from sqlalchemy import Column, Integer, String, DateTime, JSON
from app.core.database import Base

class AuditLog(Base):
    """
    Foundational model for NATO-aligned audit trails.
    Tracks all administrative and operational changes.
    """
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    user_id = Column(String, nullable=True, index=True)  # System actions might have null user_id
    
    action = Column(String, nullable=False, index=True)  # e.g., 'alert.resolve', 'risk_threshold.update'
    resource_id = Column(String, nullable=True)
    resource_type = Column(String, nullable=True)
    
    change_summary = Column(String, nullable=False)
    details = Column(JSON, nullable=True)  # Diff or before/after state
    
    correlation_id = Column(String, nullable=True, index=True)
