"""Explainable AIS/SAR fusion for critical-infrastructure monitoring."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Iterable
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy.orm import Session

from app.core.config import settings
from app.modules.fusion.fused_rules import nearest_cable_segment
from app.modules.observations.models import FusionEvent, Observation
from app.tracking.features import haversine_m
from app.infrastructure.ingest.loaders import AisPoint

VESSEL_ACTIVITY_NEAR_CABLE = "VESSEL_ACTIVITY_NEAR_CABLE"
AIS_SAR_POSITION_CONFLICT = "AIS_SAR_POSITION_CONFLICT"
UNMATCHED_SAR_NEAR_CABLE = "UNMATCHED_SAR_NEAR_CABLE"
AIS_SILENCE_NEAR_CABLE = "AIS_SILENCE_NEAR_CABLE"
FUSION_VERSION = "ais-sar-cable/v1"


def _utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _event_id(event_type: str, observation_ids: Iterable[str]) -> str:
    material = f"{event_type}:{':'.join(sorted(observation_ids))}"
    return str(uuid5(NAMESPACE_URL, material))


def _confidence(score: float, method: str, notes: str) -> dict[str, Any]:
    return {
        "score": round(max(0.0, min(1.0, score)), 4),
        "method": method,
        "notes": notes,
    }


def _access(org_id: int) -> dict[str, Any]:
    return {
        "classification": "internal",
        "allowedRoles": ["viewer", "analyst", "admin", "super_admin"],
        "ownerOrgId": str(org_id),
    }


def _persist_event(
    db: Session,
    *,
    event_type: str,
    org_id: int,
    observations: list[Observation],
    severity: str,
    longitude: float,
    latitude: float,
    attributes: dict[str, Any],
    confidence: dict[str, Any],
) -> tuple[FusionEvent, bool]:
    observation_ids = [str(item.id) for item in observations]
    identifier = _event_id(event_type, observation_ids)
    existing = db.query(FusionEvent).filter(FusionEvent.id == identifier).first()
    if existing is not None:
        return existing, False
    now = datetime.now(timezone.utc)
    event = FusionEvent(
        id=identifier,
        organisation_id=org_id,
        event_type=event_type,
        entity_ids=sorted({item.entity_id for item in observations}),
        observation_ids=observation_ids,
        occurred_at=max(_utc(item.observed_at) for item in observations),
        severity=severity,
        longitude=longitude,
        latitude=latitude,
        attributes={"fusionVersion": FUSION_VERSION, **attributes},
        confidence=confidence,
        provenance={
            "source": "aegisais-fusion",
            "processor": FUSION_VERSION,
            "ingestedAt": now.isoformat(),
            "lineage": observation_ids,
        },
        access=_access(org_id),
    )
    db.add(event)
    db.flush()
    return event, True


def _distance_allowance_m(ais: Observation, sar: Observation) -> float:
    elapsed_hours = abs((_utc(sar.observed_at) - _utc(ais.observed_at)).total_seconds()) / 3600.0
    sog = float((ais.properties or {}).get("sog") or 0.0)
    travelled_m = sog * 1852.0 * elapsed_hours
    # One kilometre covers typical source/geolocation uncertainty; elapsed
    # travel expands the gate, but it is never allowed beyond the 5 km cap.
    return min(settings.fused_sar_max_distance_m, 1000.0 + travelled_m)


def _recent_ais(db: Session, sar: Observation) -> list[Observation]:
    window = timedelta(seconds=settings.fused_sar_time_window_sec)
    return (
        db.query(Observation)
        .filter(
            Observation.organisation_id == sar.organisation_id,
            Observation.layer_id.in_([
                "maritime.ais.terrestrial",
                "maritime.ais.satellite",
            ]),
            Observation.observed_at >= sar.observed_at - window,
            Observation.observed_at <= sar.observed_at + window,
        )
        .all()
    )


def _model_context(db: Session, observation: Observation) -> dict[str, Any]:
    from app.detection.isolation_forest import default_scorer

    rows = (
        db.query(Observation)
        .filter(
            Observation.organisation_id == observation.organisation_id,
            Observation.entity_id == observation.entity_id,
            Observation.layer_id.in_(["maritime.ais.terrestrial", "maritime.ais.satellite"]),
            Observation.observed_at <= observation.observed_at,
        )
        .order_by(Observation.observed_at.desc())
        .limit(10)
        .all()
    )
    track = [
        AisPoint(
            mmsi=str((row.properties or {}).get("mmsi") or row.entity_id.rsplit(":", 1)[-1]),
            timestamp=_utc(row.observed_at),
            lat=row.latitude,
            lon=row.longitude,
            sog=(row.properties or {}).get("sog"),
            cog=(row.properties or {}).get("cog"),
            heading=(row.properties or {}).get("heading"),
        )
        for row in reversed(rows)
    ]
    if len(track) < 2:
        return {"state": "degraded", "reason": "insufficient_track_window"}
    scored = default_scorer.score(track)
    return {
        "state": scored.get("state"),
        "modelVersion": scored.get("model_version"),
        "anomalyPercentile": scored.get("anomaly_percentile"),
        "thresholdPercentile": scored.get("threshold_percentile"),
        "isAnomaly": scored.get("is_anomaly"),
        "scoreSemantics": "empirical percentile, not probability",
        "topFactors": scored.get("explanation", []),
        "reason": scored.get("reason"),
    }


def associate_sar_batch(
    sar_observations: list[Observation],
    ais_observations: list[Observation],
) -> dict[str, tuple[Observation, float, float]]:
    """Deterministic one-to-one minimum-cost assignment within uncertainty gates.

    Candidate pairs are globally sorted by normalized distance, time offset and
    stable IDs.  This produces a deterministic bipartite matching without
    requiring a heavyweight optimizer in the online worker.
    """
    candidates: list[tuple[float, float, str, str, Observation, Observation, float]] = []
    for sar in sar_observations:
        explicit_mmsi = str((sar.properties or {}).get("matchedMmsi") or "")
        for ais in ais_observations:
            if explicit_mmsi and ais.entity_id != f"vessel:mmsi:{explicit_mmsi}":
                continue
            dt = abs((_utc(sar.observed_at) - _utc(ais.observed_at)).total_seconds())
            if dt > settings.fused_sar_time_window_sec:
                continue
            distance = haversine_m(sar.latitude, sar.longitude, ais.latitude, ais.longitude)
            allowance = _distance_allowance_m(ais, sar)
            cost = distance / max(allowance, 1.0)
            if cost <= 1.0:
                candidates.append((cost, dt, str(sar.id), str(ais.id), sar, ais, allowance))
    candidates.sort(key=lambda item: item[:4])
    assigned_sar: set[str] = set()
    assigned_ais: set[str] = set()
    matches: dict[str, tuple[Observation, float, float]] = {}
    for cost, _dt, sar_id, ais_id, sar, ais, allowance in candidates:
        if sar_id in assigned_sar or ais_id in assigned_ais:
            continue
        distance = cost * allowance
        matches[sar_id] = (ais, distance, allowance)
        assigned_sar.add(sar_id)
        assigned_ais.add(ais_id)
    return matches


def fuse_observation(db: Session, observation: Observation) -> list[FusionEvent]:
    created_events: list[FusionEvent] = []
    segment, distance_to_cable = nearest_cable_segment(observation.latitude, observation.longitude)
    near_cable = distance_to_cable <= settings.fused_cable_proximity_m

    if observation.layer_id.startswith("maritime.ais") and near_cable:
        sog = float((observation.properties or {}).get("sog") or 0.0)
        if sog <= 3.0:
            model_context = _model_context(db, observation)
            model_support = 0.1 if model_context.get("isAnomaly") is True else 0.0
            confidence_score = 0.55 + min(0.2, (3.0 - sog) / 15.0) + model_support
            event, created = _persist_event(
                db,
                event_type=VESSEL_ACTIVITY_NEAR_CABLE,
                org_id=observation.organisation_id,
                observations=[observation],
                severity="medium",
                longitude=observation.longitude,
                latitude=observation.latitude,
                attributes={
                    "reason": "Low-speed vessel activity inside cable protection threshold",
                    "distanceToCableM": round(distance_to_cable, 2),
                    "proximityThresholdM": settings.fused_cable_proximity_m,
                    "sogKnots": sog,
                    "cableSegment": segment,
                    "sensorSupport": [observation.layer_id],
                    "model": model_context,
                },
                confidence=_confidence(
                    confidence_score,
                    "single_sensor_rule",
                    "AIS-only event; awaiting independent corroboration",
                ),
            )
            if created:
                created_events.append(event)

    if observation.layer_id == "maritime.sar.gfw" and near_cable:
        ais_candidates = _recent_ais(db, observation)
        match = associate_sar_batch([observation], ais_candidates).get(str(observation.id))
        explicit_mmsi = str((observation.properties or {}).get("matchedMmsi") or "")

        if match:
            ais, distance_m, allowance_m = match
            # A close independent match corroborates the cable activity.  A
            # provider-declared MMSI with a position outside the normal 1 km
            # uncertainty envelope is retained as a conflict signal.
            if explicit_mmsi and distance_m > 1000.0:
                event_type = AIS_SAR_POSITION_CONFLICT
                severity = "high"
                reason = "Independent SAR position conflicts with AIS position"
                confidence_score = 0.86
            else:
                event_type = VESSEL_ACTIVITY_NEAR_CABLE
                severity = "high"
                reason = "AIS activity near cable independently corroborated by SAR"
                confidence_score = 0.9
            event, created = _persist_event(
                db,
                event_type=event_type,
                org_id=observation.organisation_id,
                observations=[ais, observation],
                severity=severity,
                longitude=observation.longitude,
                latitude=observation.latitude,
                attributes={
                    "reason": reason,
                    "distanceToCableM": round(distance_to_cable, 2),
                    "proximityThresholdM": settings.fused_cable_proximity_m,
                    "associationDistanceM": round(distance_m, 2),
                    "associationAllowanceM": round(allowance_m, 2),
                    "cableSegment": segment,
                    "sensorSupport": [ais.layer_id, observation.layer_id],
                },
                confidence=_confidence(confidence_score, "independent_sensor_corroboration", reason),
            )
        else:
            prior_cutoff = observation.observed_at - timedelta(seconds=settings.ais_silence_threshold_sec)
            prior = (
                db.query(Observation)
                .filter(
                    Observation.organisation_id == observation.organisation_id,
                    Observation.layer_id.in_(["maritime.ais.terrestrial", "maritime.ais.satellite"]),
                    Observation.observed_at <= prior_cutoff,
                )
                .order_by(Observation.observed_at.desc())
                .first()
            )
            silence_sec = (
                (_utc(observation.observed_at) - _utc(prior.observed_at)).total_seconds() if prior else None
            )
            model_context = _model_context(db, prior) if prior is not None else {"state": "degraded", "reason": "no_prior_ais_track"}
            event, created = _persist_event(
                db,
                event_type=UNMATCHED_SAR_NEAR_CABLE,
                org_id=observation.organisation_id,
                observations=[item for item in [prior, observation] if item is not None],
                severity="critical" if prior is not None else "high",
                longitude=observation.longitude,
                latitude=observation.latitude,
                attributes={
                    "reason": "SAR target near cable has no AIS match in the fusion window",
                    "distanceToCableM": round(distance_to_cable, 2),
                    "proximityThresholdM": settings.fused_cable_proximity_m,
                    "aisSilenceSec": silence_sec,
                    "aisSilenceThresholdSec": settings.ais_silence_threshold_sec,
                    "cableSegment": segment,
                    "sensorSupport": [observation.layer_id],
                    "model": model_context,
                },
                confidence=_confidence(
                    0.92 if prior else 0.78,
                    "unmatched_independent_detection",
                    "Confidence increases when a prior AIS track establishes subsequent silence",
                ),
            )
        if created:
            created_events.append(event)

    return created_events


def scan_stale_ais_near_cables(
    db: Session,
    *,
    organisation_id: int,
    now: datetime | None = None,
) -> list[FusionEvent]:
    """Prospectively detect tracks that stop reporting near a cable corridor."""
    reference_time = _utc(now or datetime.now(timezone.utc))
    cutoff = reference_time - timedelta(seconds=settings.ais_silence_threshold_sec)
    candidates = (
        db.query(Observation)
        .filter(
            Observation.organisation_id == organisation_id,
            Observation.layer_id.in_(["maritime.ais.terrestrial", "maritime.ais.satellite"]),
            Observation.observed_at <= cutoff,
        )
        .order_by(Observation.entity_id, Observation.observed_at.desc())
        .all()
    )
    latest_by_entity: dict[str, Observation] = {}
    for candidate in candidates:
        latest_by_entity.setdefault(candidate.entity_id, candidate)

    events: list[FusionEvent] = []
    for observation in latest_by_entity.values():
        _segment, distance_to_cable = nearest_cable_segment(observation.latitude, observation.longitude)
        if distance_to_cable > settings.fused_cable_proximity_m:
            continue
        silence_sec = (reference_time - _utc(observation.observed_at)).total_seconds()
        event, created = _persist_event(
            db,
            event_type=AIS_SILENCE_NEAR_CABLE,
            org_id=organisation_id,
            observations=[observation],
            severity="medium",
            longitude=observation.longitude,
            latitude=observation.latitude,
            attributes={
                "reason": "AIS track became stale inside the cable protection threshold",
                "distanceToCableM": round(distance_to_cable, 2),
                "proximityThresholdM": settings.fused_cable_proximity_m,
                "aisSilenceSec": round(silence_sec, 2),
                "aisSilenceThresholdSec": settings.ais_silence_threshold_sec,
                "sensorSupport": [observation.layer_id],
                "awaitingIndependentCorroboration": True,
                "model": _model_context(db, observation),
            },
            confidence=_confidence(
                0.6,
                "prospective_track_staleness",
                "AIS silence alone is ambiguous and requires independent corroboration",
            ),
        )
        if created:
            events.append(event)
    return events


def event_to_alert(event: FusionEvent) -> dict[str, Any]:
    severity = {"low": 25, "medium": 55, "high": 80, "critical": 95}[event.severity]
    mmsi = "unknown"
    for entity_id in event.entity_ids or []:
        if entity_id.startswith("vessel:mmsi:"):
            mmsi = entity_id.rsplit(":", 1)[-1]
            break
    evidence = {
        "eventId": event.id,
        "observationIds": event.observation_ids,
        "confidence": event.confidence,
        "provenance": event.provenance,
        **(event.attributes or {}),
    }
    return {
        "organisation_id": event.organisation_id,
        "timestamp": event.occurred_at.isoformat(),
        "mmsi": mmsi,
        "type": event.event_type,
        "severity": severity,
        "summary": str(event.attributes.get("reason") or event.event_type),
        "evidence": evidence,
        "confidence": event.confidence,
        "provenance": event.provenance,
        "fusion_event_id": event.id,
    }
