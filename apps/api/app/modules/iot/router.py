from __future__ import annotations

from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.middleware.rate_limit import api_read_rate_limit, api_write_rate_limit
from app.modules.auth.dependencies import require_admin, require_analyst
from app.modules.iot.schemas import (
    DeviceCreate,
    EdgeBatchCreate,
    EdgeBatchOut,
    EdgeBatchReplayOut,
    IotOverviewOut,
    MqttIngestRequest,
    DeviceHeartbeatCreate,
    DeviceHeartbeatOut,
    DeviceOut,
    NmeaIngestRequest,
    TelemetryEventOut,
    DeviceUpdate,
)
from app.modules.iot.edge_ingest import queue_edge_batch
from app.modules.iot.edge_sync import replay_queued_edge_batch
from app.modules.iot.service import (
    create_device,
    create_heartbeat,
    get_device,
    get_iot_overview,
    ingest_mqtt_telemetry,
    ingest_nmea_telemetry,
    list_devices,
    list_heartbeats,
    list_telemetry_events,
    update_device,
)

router = APIRouter()


@router.get("/devices", response_model=list[DeviceOut])
def api_list_devices(
    _: Annotated[None, Depends(api_read_rate_limit)],
    db: Session = Depends(get_db),
    user: Any = Depends(require_analyst),
    device_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    asset_id: Optional[int] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    return list_devices(
        db,
        user=user,
        device_type=device_type,
        status=status,
        asset_id=asset_id,
        limit=limit,
        offset=offset,
    )


@router.post("/devices", response_model=DeviceOut)
def api_create_device(
    _: Annotated[None, Depends(api_write_rate_limit)],
    body: DeviceCreate,
    db: Session = Depends(get_db),
    actor: Any = Depends(require_admin),
):
    return create_device(db, body, actor=actor)


@router.get("/devices/{device_id}", response_model=DeviceOut)
def api_get_device(
    device_id: int,
    _: Annotated[None, Depends(api_read_rate_limit)],
    db: Session = Depends(get_db),
    user: Any = Depends(require_analyst),
):
    return get_device(db, device_id, user=user)


@router.patch("/devices/{device_id}", response_model=DeviceOut)
def api_update_device(
    device_id: int,
    _: Annotated[None, Depends(api_write_rate_limit)],
    body: DeviceUpdate,
    db: Session = Depends(get_db),
    actor: Any = Depends(require_admin),
):
    return update_device(db, device_id, body, actor=actor)


@router.get("/devices/{device_id}/heartbeats", response_model=list[DeviceHeartbeatOut])
def api_list_heartbeats(
    device_id: int,
    _: Annotated[None, Depends(api_read_rate_limit)],
    db: Session = Depends(get_db),
    user: Any = Depends(require_analyst),
    limit: int = Query(100, ge=1, le=500),
):
    return list_heartbeats(db, device_id, user=user, limit=limit)


@router.post("/devices/{device_id}/heartbeats", response_model=DeviceHeartbeatOut)
def api_create_heartbeat(
    device_id: int,
    _: Annotated[None, Depends(api_write_rate_limit)],
    body: DeviceHeartbeatCreate,
    db: Session = Depends(get_db),
    actor: Any = Depends(require_admin),
):
    return create_heartbeat(db, device_id, body, actor=actor)


@router.post("/telemetry/mqtt", response_model=TelemetryEventOut)
def api_ingest_mqtt_telemetry(
    _: Annotated[None, Depends(api_write_rate_limit)],
    body: MqttIngestRequest,
    db: Session = Depends(get_db),
    actor: Any = Depends(require_admin),
):
    return ingest_mqtt_telemetry(db, body, actor=actor)


@router.post("/telemetry/nmea", response_model=TelemetryEventOut)
def api_ingest_nmea_telemetry(
    _: Annotated[None, Depends(api_write_rate_limit)],
    body: NmeaIngestRequest,
    db: Session = Depends(get_db),
    actor: Any = Depends(require_admin),
):
    return ingest_nmea_telemetry(db, body, actor=actor)


@router.get("/telemetry/events", response_model=list[TelemetryEventOut])
def api_list_telemetry_events(
    _: Annotated[None, Depends(api_read_rate_limit)],
    db: Session = Depends(get_db),
    user: Any = Depends(require_analyst),
    device_id: Optional[int] = Query(None),
    asset_id: Optional[int] = Query(None),
    limit: int = Query(50, ge=1, le=200),
):
    return list_telemetry_events(db, user=user, device_id=device_id, asset_id=asset_id, limit=limit)


@router.post("/devices/{device_id}/edge/batches", response_model=EdgeBatchOut)
def api_queue_edge_batch(
    device_id: int,
    _: Annotated[None, Depends(api_write_rate_limit)],
    body: EdgeBatchCreate,
    db: Session = Depends(get_db),
    actor: Any = Depends(require_admin),
):
    return queue_edge_batch(db, device_id, body, actor=actor)


@router.post("/edge/batches/{batch_id}/replay", response_model=EdgeBatchReplayOut)
def api_replay_edge_batch(
    batch_id: int,
    _: Annotated[None, Depends(api_write_rate_limit)],
    db: Session = Depends(get_db),
    actor: Any = Depends(require_admin),
):
    return replay_queued_edge_batch(db, batch_id, actor=actor)


@router.get("/overview", response_model=IotOverviewOut)
def api_iot_overview(
    _: Annotated[None, Depends(api_read_rate_limit)],
    db: Session = Depends(get_db),
    user: Any = Depends(require_analyst),
    limit: int = Query(10, ge=1, le=50),
):
    return get_iot_overview(db, user=user, limit=limit)
