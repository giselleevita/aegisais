"""Application service for vessel and track queries."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Optional

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.validators import validate_mmsi
from app.core.database import get_db
from app.modules.auth.models import User
from app.modules.auth.org_scope import is_super_admin
from app.modules.vessels.mappers import vessel_latest_to_out, vessel_position_to_out
from app.modules.vessels.models import VesselLatest, VesselPosition
from app.modules.vessels.schemas import VesselLatestOut, VesselPositionOut


class VesselService:
    def __init__(self, db: Session):
        self._db = db

    def list_vessels(
        self,
        *,
        scope_user: User,
        min_severity: int,
        limit: int,
        offset: int = 0,
    ) -> list[VesselLatestOut]:
        q = (
            self._db.query(VesselLatest)
            .filter(VesselLatest.last_alert_severity >= min_severity)
            .order_by(VesselLatest.timestamp.desc())
        )
        if not is_super_admin(scope_user):
            q = q.filter(VesselLatest.organisation_id == scope_user.organisation_id)
        return [vessel_latest_to_out(v) for v in q.offset(offset).limit(limit).all()]

    def get_vessel(self, mmsi: str, *, scope_user: User) -> VesselLatestOut:
        validate_mmsi(mmsi)
        q = self._db.query(VesselLatest).filter(VesselLatest.mmsi == mmsi)
        if not is_super_admin(scope_user):
            q = q.filter(VesselLatest.organisation_id == scope_user.organisation_id)
        vessel = q.first()
        if vessel is None:
            raise HTTPException(
                status_code=404, detail=f"Vessel with MMSI {mmsi} not found"
            )
        return vessel_latest_to_out(vessel)

    def get_track(
        self,
        mmsi: str,
        *,
        scope_user: User,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000,
    ) -> list[VesselPositionOut]:
        validate_mmsi(mmsi)
        query = self._db.query(VesselPosition).filter(VesselPosition.mmsi == mmsi)
        if not is_super_admin(scope_user):
            query = query.filter(VesselPosition.organisation_id == scope_user.organisation_id)

        if start_time:
            query = query.filter(VesselPosition.timestamp >= start_time)
        if end_time:
            query = query.filter(VesselPosition.timestamp <= end_time)

        positions = query.order_by(VesselPosition.timestamp.asc()).limit(limit).all()
        return [vessel_position_to_out(p) for p in positions]


def get_vessel_service(db: Session = Depends(get_db)) -> VesselService:
    return VesselService(db)


VesselServiceDep = Annotated[VesselService, Depends(get_vessel_service)]
