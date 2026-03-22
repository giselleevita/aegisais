from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.modules.audit.models import AuditLog
from app.modules.auth.models import User
from app.modules.auth.org_scope import apply_org_filter


class AuditService:
    """
    Service for managing and persisting audit logs.
    """

    @staticmethod
    def log_event(
        db: Session,
        action: str,
        change_summary: str,
        *,
        organisation_id: int,
        user_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
    ) -> AuditLog:
        """
        Record a new audit event.
        """
        log_entry = AuditLog(
            timestamp=datetime.now(timezone.utc),
            organisation_id=organisation_id,
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

    @staticmethod
    def list_logs(
        db: Session,
        *,
        scope_user: User,
        action: Optional[str] = None,
        user_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AuditLog]:
        """Return audit rows newest first (admin UI / compliance export)."""
        q = db.query(AuditLog).order_by(AuditLog.timestamp.desc())
        q = apply_org_filter(q, AuditLog, scope_user)
        if action:
            q = q.filter(AuditLog.action == action)
        if user_id:
            q = q.filter(AuditLog.user_id == user_id)
        if resource_type:
            q = q.filter(AuditLog.resource_type == resource_type)
        if start_time:
            q = q.filter(AuditLog.timestamp >= start_time)
        if end_time:
            q = q.filter(AuditLog.timestamp <= end_time)
        return q.offset(offset).limit(limit).all()

    @staticmethod
    def list_logs_for_export(
        db: Session,
        *,
        scope_user: User,
        action: Optional[str] = None,
        user_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        max_rows: int = 10000,
    ) -> List[AuditLog]:
        """Same filters as list_logs; capped download for admin CSV export."""
        q = db.query(AuditLog).order_by(AuditLog.timestamp.desc())
        q = apply_org_filter(q, AuditLog, scope_user)
        if action:
            q = q.filter(AuditLog.action == action)
        if user_id:
            q = q.filter(AuditLog.user_id == user_id)
        if resource_type:
            q = q.filter(AuditLog.resource_type == resource_type)
        if start_time:
            q = q.filter(AuditLog.timestamp >= start_time)
        if end_time:
            q = q.filter(AuditLog.timestamp <= end_time)
        return q.limit(max_rows).all()
