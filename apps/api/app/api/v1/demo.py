"""Admin-controlled, deterministic festival scenario playback."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.infrastructure.ingest.loaders import AisPoint
from app.infrastructure.messaging.publisher import publisher
from app.modules.alerts.models import Alert
from app.modules.auth.dependencies import require_admin
from app.modules.observations.models import FusionEvent, Observation
from app.modules.observations.providers import ReplayObservationProvider
from app.modules.incidents.models import Incident
from app.modules.vessels.models import VesselLatest, VesselPosition
from app.services.pipeline import enqueue_point

router = APIRouter()
_task: asyncio.Task[None] | None = None
_state: dict[str, Any] = {
    "state": "idle",
    "scenario": "baltic-cable",
    "emitted": 0,
    "total": 0,
    "error": None,
    "startedAt": None,
    "completedAt": None,
}


def _resolve_scenario_path() -> Path:
    configured = Path(settings.demo_scenario_path)
    if configured.exists():
        return configured
    repository_candidate = Path(__file__).resolve().parents[5] / settings.demo_scenario_path
    if repository_candidate.exists():
        return repository_candidate
    raise FileNotFoundError(settings.demo_scenario_path)


async def _play(organisation_id: int, speed: float) -> None:
    global _state
    try:
        path = _resolve_scenario_path()
        payload = json.loads(path.read_text(encoding="utf-8"))
        observations = ReplayObservationProvider(path).load(organisation_id)
        playback_delays = [float(row.get("playbackOffsetSec", index * 10)) for index, row in enumerate(payload["observations"])]
        first_observed = min(item.observedAt for item in observations)
        logical_base = datetime.now(timezone.utc)
        previous_delay = 0.0
        _state.update({"state": "running", "total": len(observations), "emitted": 0})
        for observation, delay in zip(observations, playback_delays):
            wait_seconds = max(0.0, delay - previous_delay) / speed
            if wait_seconds:
                await asyncio.sleep(wait_seconds)
            previous_delay = delay
            logical_offset = observation.observedAt - first_observed
            observation = observation.model_copy(update={"observedAt": logical_base + logical_offset})
            if observation.layerId.startswith("maritime.ais"):
                props = observation.properties
                enqueue_point(
                    AisPoint(
                        mmsi=str(props["mmsi"]),
                        timestamp=observation.observedAt,
                        lat=observation.latitude,
                        lon=observation.longitude,
                        sog=props.get("sog"),
                        cog=props.get("cog"),
                        heading=props.get("heading"),
                    ),
                    organisation_id=organisation_id,
                    source="festival-replay",
                    layer_id=observation.layerId,
                    confidence=observation.confidence.score,
                    provenance=observation.provenance.model_dump(mode="json", exclude_none=True),
                )
            else:
                publisher.publish(
                    settings.stream_observations,
                    observation.model_dump(mode="json", exclude_none=True),
                )
            _state["emitted"] += 1
        _state.update({"state": "completed", "completedAt": datetime.now(timezone.utc).isoformat()})
    except asyncio.CancelledError:
        _state["state"] = "idle"
        raise
    except Exception as exc:
        _state.update({"state": "failed", "error": f"{type(exc).__name__}: {exc}"})


@router.post("/demo/scenarios/baltic-cable/start")
async def start_baltic_cable_scenario(
    speed: float = Query(default=settings.demo_default_speed, gt=0, le=1000),
    admin: Any = Depends(require_admin),
):
    global _task
    if _task and not _task.done():
        raise HTTPException(status_code=409, detail="Scenario is already running")
    try:
        path = _resolve_scenario_path()
        total = len(json.loads(path.read_text(encoding="utf-8")).get("observations", []))
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Scenario fixture unavailable: {exc}") from exc
    _state.update({
        "state": "starting",
        "emitted": 0,
        "total": total,
        "error": None,
        "startedAt": datetime.now(timezone.utc).isoformat(),
        "completedAt": None,
        "speed": speed,
    })
    _task = asyncio.create_task(_play(int(admin.organisation_id), speed), name="festival-baltic-cable-demo")
    return dict(_state)


@router.post("/demo/scenarios/baltic-cable/reset")
async def reset_baltic_cable_scenario(
    db: Session = Depends(get_db),
    admin: Any = Depends(require_admin),
):
    global _task
    if _task and not _task.done():
        _task.cancel()
        try:
            await _task
        except asyncio.CancelledError:
            pass
    org_id = int(admin.organisation_id)
    source_rows = db.query(Observation.id).filter(
        Observation.organisation_id == org_id,
        Observation.provenance["source"].as_string() == "festival-replay",
    ).all()
    observation_ids = [row[0] for row in source_rows]
    alert_ids = [
        row[0]
        for row in db.query(Alert.id).filter(
            Alert.organisation_id == org_id,
            Alert.type.in_([
                "VESSEL_ACTIVITY_NEAR_CABLE",
                "AIS_SAR_POSITION_CONFLICT",
                "UNMATCHED_SAR_NEAR_CABLE",
                "AIS_SILENCE_NEAR_CABLE",
            ]),
        ).all()
    ]
    if alert_ids:
        db.query(Incident).filter(Incident.alert_id.in_(alert_ids)).delete(synchronize_session=False)
    db.query(Alert).filter(
        Alert.organisation_id == org_id,
        Alert.type.in_([
            "VESSEL_ACTIVITY_NEAR_CABLE",
            "AIS_SAR_POSITION_CONFLICT",
            "UNMATCHED_SAR_NEAR_CABLE",
            "AIS_SILENCE_NEAR_CABLE",
        ]),
    ).delete(synchronize_session=False)
    db.query(FusionEvent).filter(FusionEvent.organisation_id == org_id).delete(synchronize_session=False)
    if observation_ids:
        db.query(Observation).filter(Observation.id.in_(observation_ids)).delete(synchronize_session=False)
    # The legacy map/API projection is derived from the replay stream. Clear
    # only rows owned by this scenario so every rehearsal starts from the same
    # state without touching live or third-party vessel data.
    db.query(VesselPosition).filter(
        VesselPosition.organisation_id == org_id,
        VesselPosition.source == "festival-replay",
    ).delete(synchronize_session=False)
    db.query(VesselLatest).filter(
        VesselLatest.organisation_id == org_id,
        VesselLatest.source == "festival-replay",
    ).delete(synchronize_session=False)
    db.commit()
    _state.update({"state": "idle", "emitted": 0, "total": 0, "error": None, "startedAt": None, "completedAt": None})
    return dict(_state)


@router.get("/demo/scenarios/baltic-cable/status")
def baltic_cable_scenario_status(
    db: Session = Depends(get_db),
    admin: Any = Depends(require_admin),
):
    org_id = int(admin.organisation_id)
    return {
        **_state,
        "persistedObservations": db.query(Observation).filter(Observation.organisation_id == org_id).count(),
        "fusionEvents": db.query(FusionEvent).filter(FusionEvent.organisation_id == org_id).count(),
        "fusionAlerts": db.query(Alert).filter(
            Alert.organisation_id == org_id,
            Alert.type.in_([
                "VESSEL_ACTIVITY_NEAR_CABLE",
                "AIS_SAR_POSITION_CONFLICT",
                "UNMATCHED_SAR_NEAR_CABLE",
                "AIS_SILENCE_NEAR_CABLE",
            ]),
        ).count(),
        "festivalPositions": db.query(VesselPosition).filter(
            VesselPosition.organisation_id == org_id,
            VesselPosition.source == "festival-replay",
        ).count(),
        "festivalVessels": db.query(VesselLatest).filter(
            VesselLatest.organisation_id == org_id,
            VesselLatest.source == "festival-replay",
        ).count(),
    }
