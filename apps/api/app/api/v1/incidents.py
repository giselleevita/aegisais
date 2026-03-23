from typing import Annotated, Optional, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.middleware.rate_limit import api_read_rate_limit, api_write_rate_limit
from app.modules.auth.dependencies import require_analyst, get_org_scope
from app.modules.incidents.schemas import IncidentOut, IncidentUpdate
from app.modules.incidents.service import list_incidents, get_incident, update_incident

router = APIRouter()


@router.get("/incidents", response_model=list[IncidentOut])
def api_list_incidents(
    _: Annotated[None, Depends(api_read_rate_limit)],
    db: Session = Depends(get_db),
    user: Any = Depends(get_org_scope),
    status: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    return list_incidents(db, user=user, status=status, limit=limit, offset=offset)


@router.get("/incidents/{incident_id}", response_model=IncidentOut)
def api_get_incident(
    incident_id: int,
    _: Annotated[None, Depends(api_read_rate_limit)],
    db: Session = Depends(get_db),
    user: Any = Depends(get_org_scope),
):
    return get_incident(db, incident_id, user=user)


@router.patch("/incidents/{incident_id}", response_model=IncidentOut)
def api_patch_incident(
    incident_id: int,
    _: Annotated[None, Depends(api_write_rate_limit)],
    payload: IncidentUpdate = ...,
    db: Session = Depends(get_db),
    actor: Any = Depends(require_analyst),
):
    return update_incident(db, incident_id, payload, actor=actor)

