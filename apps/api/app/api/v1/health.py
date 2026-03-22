"""Health check and system status endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timezone
from app.core.database import get_db

router = APIRouter()

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
