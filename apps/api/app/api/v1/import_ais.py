"""Batch AIS vessel data import endpoint.

Accepts a JSON array of AIS position records and bulk-inserts them into
the VesselLatest / VesselPosition tables via the existing database session.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.api.validators import validate_mmsi
from app.core.database import get_db
from app.middleware.rate_limit import upload_file_rate_limit
from app.modules.auth.dependencies import require_admin
from app.modules.vessels.models import VesselLatest, VesselPosition

log = logging.getLogger("aegisais.import_ais")

router = APIRouter()

_MAX_BATCH = 5_000


class AisPositionIn(BaseModel):
    mmsi: str = Field(..., min_length=9, max_length=9, description="9-digit MMSI")
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    speed: float | None = Field(default=None, ge=0.0, le=102.2)
    course: float | None = Field(default=None, ge=0.0, lt=360.0)
    heading: int | None = Field(default=None, ge=0, le=511)
    nav_status: int | None = Field(default=None, ge=0, le=15)
    timestamp: datetime | None = Field(default=None)
    vessel_name: str | None = Field(default=None, max_length=255)
    imo: str | None = Field(default=None, max_length=20)
    call_sign: str | None = Field(default=None, max_length=20)
    ship_type: int | None = Field(default=None, ge=0, le=99)

    @field_validator("mmsi")
    @classmethod
    def _must_be_digits(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("MMSI must be 9 digits")
        return v


class BatchImportRequest(BaseModel):
    records: list[AisPositionIn] = Field(..., min_length=1)


class BatchImportResponse(BaseModel):
    imported: int
    skipped: int
    errors: list[str] = []


@router.post(
    "/import/ais",
    response_model=BatchImportResponse,
    status_code=status.HTTP_207_MULTI_STATUS,
    summary="Bulk-import AIS vessel position records",
    description=(
        "Accepts up to 5,000 AIS position records per call. "
        "Each record upserts VesselLatest and appends to VesselPosition. "
        "Admin role required."
    ),
)
def batch_import_ais(
    _: Annotated[None, Depends(upload_file_rate_limit)],
    body: BatchImportRequest,
    db: Session = Depends(get_db),
    admin: Any = Depends(require_admin),
) -> BatchImportResponse:
    if len(body.records) > _MAX_BATCH:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Batch exceeds maximum of {_MAX_BATCH} records",
        )

    imported = 0
    skipped = 0
    errors: list[str] = []

    for rec in body.records:
        try:
            validate_mmsi(rec.mmsi)
        except HTTPException:
            errors.append(f"Invalid MMSI {rec.mmsi!r}")
            skipped += 1
            continue

        ts = rec.timestamp or datetime.now(timezone.utc)

        # Upsert VesselLatest (keep the most recent)
        existing: VesselLatest | None = (
            db.query(VesselLatest).filter(VesselLatest.mmsi == rec.mmsi).first()
        )
        if existing is None or (ts > existing.timestamp):
            if existing is None:
                vessel = VesselLatest(
                    mmsi=rec.mmsi,
                    lat=rec.latitude,
                    lon=rec.longitude,
                    sog=rec.speed,
                    cog=rec.course,
                    heading=rec.heading,
                    timestamp=ts,
                )
                db.add(vessel)
            else:
                setattr(existing, "lat", rec.latitude)
                setattr(existing, "lon", rec.longitude)
                setattr(existing, "sog", rec.speed)
                setattr(existing, "cog", rec.course)
                setattr(existing, "heading", rec.heading)
                setattr(existing, "timestamp", ts)

        # Append VesselPosition track record
        position = VesselPosition(
            mmsi=rec.mmsi,
            lat=rec.latitude,
            lon=rec.longitude,
            sog=rec.speed,
            cog=rec.course,
            heading=rec.heading,
            timestamp=ts,
        )
        db.add(position)
        imported += 1

    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        log.error("batch_import_commit_failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database commit failed",
        ) from exc

    log.info("ais_batch_import imported=%d skipped=%d", imported, skipped)
    return BatchImportResponse(imported=imported, skipped=skipped, errors=errors)
