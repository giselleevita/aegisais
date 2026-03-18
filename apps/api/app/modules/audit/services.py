from datetime import datetime, timezone
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session
from app.modules.audit.models import AuditLog

class AuditService:
    """
    Service for managing and persisting audit logs.
    """

    @staticmethod
    def log_event(
        db: Session,
        action: str,
        change_summary: str,
        user_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None
    ) -> AuditLog:
        """
        Record a new audit event.
        """
        log_entry = AuditLog(
            timestamp=datetime.now(timezone.utc),
            user_id=user_id,
            action=action,
            resource_id=resource_id,
            resource_type=resource_type,
            change_summary=change_summary,
            details=details,
            correlation_id=correlation_id
        )
        db.add(log_entry)
        db.flush()  # Ensures ID is generated if needed without full commit
        return log_entry
