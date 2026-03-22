"""
Satellite AIS (S-AIS) routes.

See package docstring in ``app.modules.sais`` for env vars and behaviour.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app.core.config import settings
from app.modules.auth.dependencies import require_analyst
from app.modules.auth.models import User

router = APIRouter()


def _mask_api_key(key: str) -> str | None:
    if not key:
        return None
    return "***"


def _sais_status_payload() -> dict:
    return {
        "provider": settings.SAIS_PROVIDER,
        "api_base_url": settings.SAIS_API_BASE_URL or None,
        "api_key_configured": bool(settings.SAIS_API_KEY),
        "api_key_masked": _mask_api_key(settings.SAIS_API_KEY),
    }


@router.get("/health")
async def sais_health(_user: User = Depends(require_analyst)):
    """Lightweight S-AIS module health (auth: analyst or admin)."""
    return {
        "status": "ok",
        "module": "sais",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/status")
async def sais_status(_user: User = Depends(require_analyst)):
    """Provider configuration snapshot; API key is never returned in full (auth: analyst or admin)."""
    return _sais_status_payload()
