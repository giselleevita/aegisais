"""Shared SQLAlchemy filter chain for Alert queries (list + exports)."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import case, select
from sqlalchemy.orm import Query

from app.api.validators import validate_alert_status, validate_alert_type, validate_mmsi
from app.modules.alerts.models import Alert
from app.modules.vessels.models import WatchlistEntry


def apply_alert_filters(
    query: Query,
    *,
    mmsi: Optional[str] = None,
    alert_type: Optional[str] = None,
    status: Optional[str] = None,
    min_severity: int = 0,
    max_severity: int = 100,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
) -> Query:
    """Apply the same filters as GET /v1/alerts (validation included)."""
    if mmsi:
        validate_mmsi(mmsi)
        query = query.filter(Alert.mmsi == mmsi)
    if alert_type:
        validate_alert_type(alert_type)
        query = query.filter(Alert.type == alert_type)
    if status:
        validate_alert_status(status)
        query = query.filter(Alert.status == status)
    query = query.filter(Alert.severity >= min_severity)
    query = query.filter(Alert.severity <= max_severity)
    if start_time:
        query = query.filter(Alert.timestamp >= start_time)
    if end_time:
        query = query.filter(Alert.timestamp <= end_time)
    return query


def apply_watchlist_sort(query: Query) -> Query:
    """
    Order alerts so watchlisted MMSIs appear first (high → medium → low), then by time desc.
    Joins watchlist rows that match the alert's organisation.
    """
    wl_subq = (
        select(
            WatchlistEntry.mmsi,
            WatchlistEntry.priority,
            WatchlistEntry.organisation_id,
        )
        .where(WatchlistEntry.is_active.is_(True))
        .subquery()
    )
    query = query.outerjoin(
        wl_subq,
        (Alert.mmsi == wl_subq.c.mmsi)
        & (Alert.organisation_id == wl_subq.c.organisation_id),
    )
    prio = case(
        (wl_subq.c.priority == "high", 0),
        (wl_subq.c.priority == "medium", 1),
        (wl_subq.c.priority == "low", 2),
        else_=3,
    )
    return query.order_by(prio, Alert.timestamp.desc())
