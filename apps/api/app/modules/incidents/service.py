from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.modules.alerts.models import Alert
from app.modules.incidents.models import Incident

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
    existing = db.query(Incident).filter(Incident.alert_id == alert.id).first()
    if existing is not None:
        return existing

    incident = Incident(
        organisation_id=alert.organisation_id,
        alert_id=alert.id,
        created_at=datetime.now(timezone.utc),
        status="open",
        title=f"Incident for alert {alert.type} ({alert.mmsi})",
        evidence_bundle=build_incident_evidence_bundle(alert),
    )
    db.add(incident)
    db.flush()
    return incident
