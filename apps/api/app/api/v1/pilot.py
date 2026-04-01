"""Pilot KPI summary endpoint for funding evidence generation."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.alerts.models import Alert
from app.modules.auth.dependencies import require_admin
from app.modules.auth.models import User
from app.services.pilot_metrics import build_pilot_kpi_summary

router = APIRouter()


@router.get("/pilot/kpi-summary")
def get_pilot_kpi_summary(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> dict[str, Any]:
    """
    Return pilot KPI summary for funding evidence generation.

    - **detection_lead_time_seconds**: median seconds from AIS ingestion to alert creation.
      Requires `ingested_at` (Unix timestamp) to be present in alert evidence JSON.
    - **false_alert_rate**: proportion of reviewed alerts marked `false_positive`.
    - **analyst_time_saved_seconds**: null until baseline workflow data is collected.

    Data is scoped to the requesting admin's organisation.
    """
    alerts = (
        db.query(Alert)
        .filter(Alert.organisation_id == admin.organisation_id)
        .all()
    )

    # Detection lead-time: derive from evidence.ingested_at where available
    detection_records: list[dict[str, float]] = []
    for alert in alerts:
        evidence = alert.evidence or {}
        ingested_at = evidence.get("ingested_at")
        if ingested_at is not None:
            try:
                detection_records.append(
                    {
                        "alert_created_at": alert.timestamp.timestamp(),
                        "ingested_at": float(ingested_at),
                    }
                )
            except (TypeError, ValueError):
                pass

    # False alert rate: alerts that have been reviewed (any terminal status)
    reviewed_statuses = {"reviewed", "resolved", "false_positive"}
    review_records: list[dict[str, bool]] = [
        {
            "reviewed": True,
            "is_false_alert": alert.status == "false_positive",
        }
        for alert in alerts
        if alert.status in reviewed_statuses
    ]

    summary = build_pilot_kpi_summary(
        detection_records=detection_records,
        review_records=review_records,
        workflow_records=[],  # populated once baseline workflow timing data is collected
    )

    return {
        "organisation_id": admin.organisation_id,
        "alert_count": len(alerts),
        "reviewed_alert_count": len(review_records),
        "kpi": summary.to_dict(),
    }
