from __future__ import annotations

from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.middleware.rate_limit import api_read_rate_limit, api_write_rate_limit
from app.modules.assets.schemas import (
    AssetCreate,
    AssetLinkCreate,
    AssetLinkOut,
    AssetOut,
    AssetPolicyCreate,
    AssetPolicyOut,
    AssetUpdate,
)
from app.modules.assets.service import (
    create_asset,
    create_asset_link,
    create_asset_policy,
    get_asset,
    list_asset_policies,
    list_assets,
    update_asset,
)
from app.modules.auth.dependencies import require_admin, require_analyst

router = APIRouter()


@router.get("/assets", response_model=list[AssetOut])
def api_list_assets(
    _: Annotated[None, Depends(api_read_rate_limit)],
    db: Session = Depends(get_db),
    user: Any = Depends(require_analyst),
    asset_type: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    return list_assets(db, user=user, asset_type=asset_type, is_active=is_active, limit=limit, offset=offset)


@router.post("/assets", response_model=AssetOut)
def api_create_asset(
    _: Annotated[None, Depends(api_write_rate_limit)],
    body: AssetCreate,
    db: Session = Depends(get_db),
    actor: Any = Depends(require_admin),
):
    return create_asset(db, body, actor=actor)


@router.get("/assets/{asset_id}", response_model=AssetOut)
def api_get_asset(
    asset_id: int,
    _: Annotated[None, Depends(api_read_rate_limit)],
    db: Session = Depends(get_db),
    user: Any = Depends(require_analyst),
):
    return get_asset(db, asset_id, user=user)


@router.patch("/assets/{asset_id}", response_model=AssetOut)
def api_update_asset(
    asset_id: int,
    _: Annotated[None, Depends(api_write_rate_limit)],
    body: AssetUpdate,
    db: Session = Depends(get_db),
    actor: Any = Depends(require_admin),
):
    return update_asset(db, asset_id, body, actor=actor)


@router.post("/assets/{asset_id}/links", response_model=AssetLinkOut)
def api_create_asset_link(
    asset_id: int,
    _: Annotated[None, Depends(api_write_rate_limit)],
    body: AssetLinkCreate,
    db: Session = Depends(get_db),
    actor: Any = Depends(require_admin),
):
    return create_asset_link(db, asset_id, body, actor=actor)


@router.get("/assets/{asset_id}/policies", response_model=list[AssetPolicyOut])
def api_list_asset_policies(
    asset_id: int,
    _: Annotated[None, Depends(api_read_rate_limit)],
    db: Session = Depends(get_db),
    user: Any = Depends(require_analyst),
):
    return list_asset_policies(db, asset_id, user=user)


@router.post("/assets/{asset_id}/policies", response_model=AssetPolicyOut)
def api_create_asset_policy(
    asset_id: int,
    _: Annotated[None, Depends(api_write_rate_limit)],
    body: AssetPolicyCreate,
    db: Session = Depends(get_db),
    actor: Any = Depends(require_admin),
):
    return create_asset_policy(db, asset_id, body, actor=actor)
