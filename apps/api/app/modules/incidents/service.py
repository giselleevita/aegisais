from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, cast

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy import desc
from fastapi import HTTPException

from app.modules.alerts.models import Alert
from app.modules.incidents.models import Incident
from app.modules.auth.models import User
from app.modules.auth.org_scope import apply_org_filter
from app.modules.audit.services import AuditService
from app.modules.incidents.schemas import IncidentOut, IncidentUpdate

INCIDENT_SCHEMA_VERSION = "1.0.0"
INCIDENT_PROVENANCE_VERSION = "2026-03-23"


class EvidenceBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = Field(default=INCIDENT_SCHEMA_VERSION)
    provenance_version: str = Field(default=INCIDENT_PROVENANCE_VERSION)
    generated_at: datetime
    source_alert: dict[str, Any]
    lineage: dict[str, Any]
    legal: dict[str, Any]


def build_incident_evidence_bundle(alert: Alert) -> dict[str, Any]:
    payload = EvidenceBundle(
        generated_at=datetime.now(timezone.utc),
        source_alert={
            "alert_id": alert.id,
            "type": alert.type,
            "severity": alert.severity,
            "timestamp": alert.timestamp.isoformat(),
            "summary": alert.summary,
            "evidence": alert.evidence,
        },
        lineage={
            "created_from": "alert_worker",
            "adapter": "ais_to_surface_activity_event",
            "rule_family": "explainable_fused_rule",
        },
        legal={
            "subsurface_tracking": "not_performed",
            "licensing_note": (
                "Use only appropriately licensed AIS/synthetic telemetry; "
                "no direct subsurface surveillance data in this evidence bundle."
            ),
        },
    )
    return payload.model_dump(mode="json")


def create_incident_from_alert(db: Session, alert: Alert) -> Incident:
    incident, _ = create_incident_from_alert_with_flag(db, alert)
    return incident


def _get_existing_incident_for_alert(db: Session, alert_id: int) -> Incident | None:
    return db.query(Incident).filter(Incident.alert_id == alert_id).first()


def create_incident_from_alert_with_flag(db: Session, alert: Alert) -> tuple[Incident, bool]:
    existing = _get_existing_incident_for_alert(db, cast(int, alert.id))
    if existing is not None:
        return existing, False

    try:
        with db.begin_nested():
            incident = Incident(
                organisation_id=alert.organisation_id,
                alert_id=alert.id,
                asset_id=getattr(alert, "asset_id", None),
                created_at=datetime.now(timezone.utc),
                status="open",
                title=f"Incident for alert {alert.type} ({alert.mmsi})",
                evidence_bundle=build_incident_evidence_bundle(alert),
            )
            db.add(incident)
            db.flush()
    except IntegrityError:
        existing = _get_existing_incident_for_alert(db, cast(int, alert.id))
        if existing is None:
            raise
        return existing, False

    return incident, True


def incident_to_out(incident: Incident) -> IncidentOut:
    return IncidentOut(
        id=cast(int, incident.id),
        organisation_id=cast(int, incident.organisation_id),
        alert_id=cast(int, incident.alert_id),
        asset_id=cast(int | None, incident.asset_id),
        created_at=cast(datetime, incident.created_at),
        status=cast(str, incident.status),
        title=cast(str, incident.title),
        evidence_bundle=cast(dict[str, Any], incident.evidence_bundle or {}),
    )


def list_incidents(
    db: Session,
    *,
    user: User,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[IncidentOut]:
    q = apply_org_filter(db.query(Incident), Incident, user)
    if status:
        q = q.filter(Incident.status == status)
    rows = q.order_by(desc(Incident.created_at)).offset(offset).limit(limit).all()
    return [incident_to_out(r) for r in rows]


def get_incident(db: Session, incident_id: int, *, user: User) -> IncidentOut:
    q = apply_org_filter(
        db.query(Incident).filter(Incident.id == incident_id),
        Incident,
        user,
    )
    row = q.first()
    if row is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident_to_out(row)


def update_incident(
    db: Session,
    incident_id: int,
    update: IncidentUpdate,
    *,
    actor: User,
) -> IncidentOut:
    q = apply_org_filter(
        db.query(Incident).filter(Incident.id == incident_id),
        Incident,
        actor,
    )
    row = q.first()
    if row is None:
        raise HTTPException(status_code=404, detail="Incident not found")

    changed: dict[str, dict[str, str]] = {}
    if update.status is not None and update.status != row.status:
        changed["status"] = {"from": row.status, "to": update.status}
        setattr(row, "status", update.status)
    if update.title is not None and update.title != row.title:
        changed["title"] = {"from": row.title, "to": update.title}
        setattr(row, "title", update.title)

    if changed:
        AuditService.log_event(
            db,
            action="incident.update",
            change_summary=f"Incident {incident_id} updated",
            organisation_id=cast(int, row.organisation_id),
            user_id=cast(str, actor.username),
            resource_type="incident",
            resource_id=str(incident_id),
            details={"changes": changed},
        )

    db.commit()
    db.refresh(row)
    return incident_to_out(row)
