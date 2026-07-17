"""Health check and system status endpoints."""
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from datetime import datetime, timezone

from app.core.config import settings
from app.core.database import get_db
from app.modules.auth.dependencies import require_admin, require_viewer_or_above
from app.modules.auth.models import User

router = APIRouter()


def _safe_feed_error(value: object) -> str | None:
    """Return a stable operator code without exposing provider payloads or keys."""
    return "feed_runtime_error" if value else None


def _satellite_ais_feed() -> dict:
    """Derive S-AIS row from env (no secrets returned)."""
    from app.modules.sais.client import get_sais_client
    client = get_sais_client()
    status = client.status
    return {
        "id": "satellite_ais",
        "label": "Satellite AIS",
        "status": status.state,
        "mode": "live" if status.state == "ready" else "disabled",
        "datasetVersion": status.provider,
        "licenceClass": "commercial",
        "errorCode": status.reason,
        "detail": status.provider,
    }


@router.get("/integrations/feeds")
async def integration_feeds_status(
    db: Session = Depends(get_db),
    user: User = Depends(require_viewer_or_above),
):
    """
    Catalog of optional external feeds (S-AIS, SAR, RF) for the analyst admin UI.
    Authenticated viewers and above; no secrets in the response.
    """
    from app.modules.observations.models import Observation

    def feed_stats(layer_id: str) -> dict:
        count, last_observed, last_ingested = db.query(
            func.count(Observation.id),
            func.max(Observation.observed_at),
            func.max(Observation.ingested_at),
        ).filter(
            Observation.organisation_id == user.organisation_id,
            Observation.layer_id == layer_id,
        ).one()
        lag = None
        if last_observed and last_ingested:
            lag = max(0.0, (last_ingested - last_observed).total_seconds())
        return {
            "lastObservedAt": last_observed.isoformat() if last_observed else None,
            "lastIngestedAt": last_ingested.isoformat() if last_ingested else None,
            "lagSeconds": lag,
            "recordCount": count,
        }

    try:
        from app.modules.itdae.ingestion.aisstream_client import aisstream_client
        ais_stats = aisstream_client.stats
        ais_status = "ready" if aisstream_client.is_running else "disconnected"
    except Exception:
        ais_stats = {}
        ais_status = "disconnected"

    feeds = [
        {
            "id": "terrestrial_ais",
            "label": "Terrestrial AIS",
            "status": ais_status,
            "mode": "live" if ais_status == "ready" else "replay",
            "datasetVersion": "aisstream-v0",
            "licenceClass": "provider_terms",
            "errorCode": _safe_feed_error(ais_stats.get("last_error")),
            **feed_stats("maritime.ais.terrestrial"),
        },
        _satellite_ais_feed(),
        {
            "id": "sar_eo",
            "label": "SAR / EO",
            "status": "ready",
            "mode": "historical_replay",
            "datasetVersion": settings.GFW_SAR_DATASET,
            "licenceClass": "noncommercial_only",
            "errorCode": None,
            "detail": "GFW/Sentinel-1 fixture adapter",
            **feed_stats("maritime.sar.gfw"),
        },
        {
            "id": "rf_sigint",
            "label": "RF (SIGINT)",
            "status": "unavailable",
            "mode": "disabled",
            "datasetVersion": None,
            "licenceClass": "partner_required",
            "errorCode": "provider_not_configured",
            "detail": None,
        },
    ]
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "feeds": feeds,
    }


@router.get("/models/anomaly/status")
async def anomaly_model_status(_user: User = Depends(require_viewer_or_above)):
    from dataclasses import asdict
    from app.detection.isolation_forest import default_scorer

    return asdict(default_scorer.status())

@router.get("/health")
async def health_check():
    """
    Basic health check endpoint.
    Returns 200 if the service is running.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "AegisAIS"
    }

async def _component_health(db: Session) -> dict:
    """Collect component health, including operator-only error details."""
    db_healthy = False
    db_error = None

    try:
        db.execute(text("SELECT 1"))
        db_healthy = True
    except Exception as e:
        db_error = str(e)

    redis_healthy = False
    redis_error = None

    try:
        from app.infrastructure.cache.redis_client import get_redis_client
        r = get_redis_client()
        r.ping()
        redis_healthy = True
    except Exception as e:
        redis_error = str(e)

    overall = "healthy" if (db_healthy and redis_healthy) else "degraded"

    return {
        "status": overall,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "AegisAIS",
        "database": {
            "connected": db_healthy,
            "error": db_error
        },
        "redis": {
            "connected": redis_healthy,
            "error": redis_error
        }
    }


@router.get("/health/detailed")
async def detailed_health_check(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Detailed component health for authenticated administrators."""
    return await _component_health(db)


@router.get("/health/ready")
async def readiness_check(db: Session = Depends(get_db)):
    """
    Kubernetes readiness endpoint.
    Returns 200 only when both database and Redis are reachable.
    """
    detailed = await _component_health(db)
    payload = {
        **detailed,
        "database": {"connected": detailed["database"]["connected"]},
        "redis": {"connected": detailed["redis"]["connected"]},
    }
    status_code = 200 if payload.get("status") == "healthy" else 503
    return JSONResponse(content=payload, status_code=status_code)

@router.get("/metrics")
async def get_metrics(db: Session = Depends(get_db)):
    """
    Get system metrics and statistics.
    """
    from app.modules.vessels.models import VesselLatest
    from app.modules.alerts.models import Alert
    from app.modules.vessels.models import VesselPosition
    
    try:
        vessel_count = db.query(VesselLatest).count()
        alert_count = db.query(Alert).count()
        position_count = db.query(VesselPosition).count()
        
        # Get alert counts by status
        from sqlalchemy import func
        alert_by_status = (
            db.query(Alert.status, func.count(Alert.id).label("count"))
            .group_by(Alert.status)
            .all()
        )
        
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "vessels": {
                "total": vessel_count
            },
            "alerts": {
                "total": alert_count,
                "by_status": {status: count for status, count in alert_by_status}
            },
            "positions": {
                "total": position_count
            }
        }
    except Exception as e:
        return {
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
