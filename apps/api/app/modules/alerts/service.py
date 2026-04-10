"""Application service for alert queries and updates."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Optional, cast

from fastapi import Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.validators import validate_alert_status
from app.core.config import settings
from app.core.database import get_db
from app.infrastructure.ws.manager import schedule_broadcast
from app.modules.audit.services import AuditService
from app.modules.alerts.mappers import alert_to_out
from app.modules.alerts.models import Alert
from app.modules.alerts.query_filters import apply_alert_filters, apply_watchlist_sort
from app.modules.alerts.schemas import AlertOut, AlertStatusUpdate
from app.modules.auth.models import User
from app.modules.auth.org_scope import apply_org_filter


class AlertService:
    def __init__(self, db: Session):
        self._db = db

    def list_alerts(
        self,
        *,
        user: User,
        mmsi: Optional[str] = None,
        alert_type: Optional[str] = None,
        min_severity: int = 0,
        max_severity: int = 100,
        status: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AlertOut]:
        query = apply_org_filter(self._db.query(Alert), Alert, user)
        query = apply_alert_filters(
            query,
            mmsi=mmsi,
            alert_type=alert_type,
            status=status,
            min_severity=min_severity,
            max_severity=max_severity,
            start_time=start_time,
            end_time=end_time,
        )
        query = apply_watchlist_sort(query)
        rows = query.offset(offset).limit(limit).all()
        return [alert_to_out(a) for a in rows]

    def list_alerts_matching(
        self,
        *,
        user: User,
        mmsi: Optional[str] = None,
        alert_type: Optional[str] = None,
        min_severity: int = 0,
        max_severity: int = 100,
        status: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> list[Alert]:
        query = apply_org_filter(self._db.query(Alert), Alert, user)
        query = apply_alert_filters(
            query,
            mmsi=mmsi,
            alert_type=alert_type,
            status=status,
            min_severity=min_severity,
            max_severity=max_severity,
            start_time=start_time,
            end_time=end_time,
        )
        query = apply_watchlist_sort(query)
        if limit is not None:
            query = query.limit(limit)
        return query.all()

    def get_alert(self, alert_id: int, *, user: User) -> AlertOut:
        q = self._db.query(Alert).filter(Alert.id == alert_id)
        q = apply_org_filter(q, Alert, user)
        alert = q.first()
        if alert is None:
            raise HTTPException(status_code=404, detail="Alert not found")
        return alert_to_out(alert)

    def get_stats_summary(
        self,
        *,
        user: User,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> dict:
        query = apply_org_filter(self._db.query(Alert), Alert, user)

        if start_time:
            query = query.filter(Alert.timestamp >= start_time)
        if end_time:
            query = query.filter(Alert.timestamp <= end_time)

        total = query.count()

        type_counts = (
            query.with_entities(Alert.type, func.count(Alert.id).label("count"))
            .group_by(Alert.type)
            .all()
        )

        avg_severity = query.with_entities(func.avg(Alert.severity)).scalar() or 0.0

        high_severity = query.filter(Alert.severity >= 70).count()
        medium_severity = query.filter(Alert.severity >= 30, Alert.severity < 70).count()
        low_severity = query.filter(Alert.severity < 30).count()

        return {
            "total": total,
            "by_type": {t: c for t, c in type_counts},
            "average_severity": round(float(avg_severity), 2),
            "by_severity_range": {
                "high": high_severity,
                "medium": medium_severity,
                "low": low_severity,
            },
        }

    def update_status(
        self,
        alert_id: int,
        update: AlertStatusUpdate,
        *,
        user: User,
        actor_username: str | None = None,
    ) -> AlertOut:
        q = self._db.query(Alert).filter(Alert.id == alert_id)
        q = apply_org_filter(q, Alert, user)
        alert = q.first()
        if alert is None:
            raise HTTPException(status_code=404, detail="Alert not found")

        validate_alert_status(update.status)

        setattr(alert, "status", update.status)
        if update.notes is not None:
            setattr(alert, "notes", update.notes)

        if settings.enable_audit_logging and actor_username:
            AuditService.log_event(
                self._db,
                action="alert.status.update",
                change_summary=f"Alert {alert_id} status set to {update.status}",
                organisation_id=cast(int, alert.organisation_id),
                user_id=actor_username,
                resource_type="alert",
                resource_id=str(alert_id),
                details={
                    "status": update.status,
                    "notes_updated": update.notes is not None,
                },
            )

        self._db.commit()
        self._db.refresh(alert)

        schedule_broadcast(
            {
                "type": "alert_status_updated",
                "alert_id": alert_id,
                "status": update.status,
                "organisation_id": cast(int, alert.organisation_id),
                "updated_by": actor_username or "unknown",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

        return alert_to_out(alert)


def get_alert_service(db: Session = Depends(get_db)) -> AlertService:
    return AlertService(db)


AlertServiceDep = Annotated[AlertService, Depends(get_alert_service)]
