"""Application service for vessel and track queries."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Optional

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.validators import validate_mmsi
from app.core.database import get_db
from app.modules.vessels.mappers import vessel_latest_to_out, vessel_position_to_out
from app.modules.vessels.models import VesselLatest, VesselPosition
from app.modules.vessels.schemas import VesselLatestOut, VesselPositionOut


class VesselService:
    def __init__(self, db: Session):
        self._db = db

    def list_vessels(self, *, min_severity: int, limit: int) -> list[VesselLatestOut]:
        q = (
            self._db.query(VesselLatest)
            .filter(VesselLatest.last_alert_severity >= min_severity)
            .order_by(VesselLatest.timestamp.desc())
            .limit(limit)
        )
        return [vessel_latest_to_out(v) for v in q.all()]

    def get_vessel(self, mmsi: str) -> VesselLatestOut:
        validate_mmsi(mmsi)
        vessel = self._db.query(VesselLatest).filter(VesselLatest.mmsi == mmsi).first()
        if vessel is None:
            raise HTTPException(
                status_code=404, detail=f"Vessel with MMSI {mmsi} not found"
            )
        return vessel_latest_to_out(vessel)

    def get_track(
        self,
        mmsi: str,
        *,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000,
    ) -> list[VesselPositionOut]:
        validate_mmsi(mmsi)
        query = self._db.query(VesselPosition).filter(VesselPosition.mmsi == mmsi)

        if start_time:
            query = query.filter(VesselPosition.timestamp >= start_time)
        if end_time:
            query = query.filter(VesselPosition.timestamp <= end_time)

        positions = query.order_by(VesselPosition.timestamp.asc()).limit(limit).all()
        return [vessel_position_to_out(p) for p in positions]


def get_vessel_service(db: Session = Depends(get_db)) -> VesselService:
    return VesselService(db)


VesselServiceDep = Annotated[VesselService, Depends(get_vessel_service)]
