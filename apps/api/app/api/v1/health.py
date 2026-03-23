"""Health check and system status endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timezone

from app.core.config import settings
from app.core.database import get_db
from app.modules.auth.dependencies import require_viewer_or_above
from app.modules.auth.models import User

router = APIRouter()


def _satellite_ais_feed() -> dict:
    """Derive S-AIS row from env (no secrets returned)."""
    prov = (settings.SAIS_PROVIDER or "none").strip().lower()
    has_key = bool(settings.SAIS_API_KEY)
    has_url = bool((settings.SAIS_API_BASE_URL or "").strip())
    if prov != "none" and has_key and has_url:
        return {
            "id": "satellite_ais",
            "label": "Satellite AIS",
            "status": "ready",
            "detail": prov,
        }
    if prov != "none" or has_key or has_url:
        return {
            "id": "satellite_ais",
            "label": "Satellite AIS",
            "status": "partial",
            "detail": "adapter not fully configured",
        }
    return {
        "id": "satellite_ais",
        "label": "Satellite AIS",
        "status": "disconnected",
        "detail": None,
    }


@router.get("/integrations/feeds")
async def integration_feeds_status(_user: User = Depends(require_viewer_or_above)):
    """
    Catalog of optional external feeds (S-AIS, SAR, RF) for the analyst admin UI.
    Authenticated viewers and above; no secrets in the response.
    """
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "feeds": [
            _satellite_ais_feed(),
            {
                "id": "sar_eo",
                "label": "SAR / EO",
                "status": "disconnected",
                "detail": None,
            },
            {
                "id": "rf_sigint",
                "label": "RF (SIGINT)",
                "status": "disconnected",
                "detail": None,
            },
        ],
    }

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

@router.get("/health/detailed")
async def detailed_health_check(db: Session = Depends(get_db)):
    """
    Detailed health check including database and Redis connectivity.
    """
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
