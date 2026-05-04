from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Any, cast

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.assets.models import Asset, AssetLink, AssetPolicy
from app.modules.assets.schemas import (
    AssetCreate,
    AssetLinkCreate,
    AssetLinkOut,
    AssetOut,
    AssetPolicyCreate,
    AssetPolicyOut,
    AssetUpdate,
)
from app.modules.audit.services import AuditService
from app.modules.auth.models import User
from app.modules.auth.org_scope import apply_org_filter


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _asset_to_out(asset: Asset) -> AssetOut:
    return AssetOut(
        id=cast(int, asset.id),
        organisation_id=cast(int, asset.organisation_id),
        asset_type=cast(str, asset.asset_type),
        name=cast(str, asset.name),
        description=cast(str | None, asset.description),
        status=cast(str, asset.status),
        criticality=cast(str, asset.criticality),
        geometry_json=cast(dict[str, Any], asset.geometry_json or {}),
        metadata_json=cast(dict[str, Any] | None, asset.metadata_json),
        is_active=cast(bool, asset.is_active),
        created_at=cast(datetime, asset.created_at),
        updated_at=cast(datetime, asset.updated_at),
    )


def _link_to_out(link: AssetLink) -> AssetLinkOut:
    return AssetLinkOut(
        id=cast(int, link.id),
        organisation_id=cast(int, link.organisation_id),
        source_asset_id=cast(int, link.source_asset_id),
        target_asset_id=cast(int, link.target_asset_id),
        relation_type=cast(str, link.relation_type),
        metadata_json=cast(dict[str, Any] | None, link.metadata_json),
        created_at=cast(datetime, link.created_at),
    )


def _policy_to_out(policy: AssetPolicy) -> AssetPolicyOut:
    return AssetPolicyOut(
        id=cast(int, policy.id),
        organisation_id=cast(int, policy.organisation_id),
        asset_id=cast(int, policy.asset_id),
        policy_type=cast(str, policy.policy_type),
        name=cast(str, policy.name),
        policy_json=cast(dict[str, Any], policy.policy_json or {}),
        active_from=cast(datetime | None, policy.active_from),
        active_to=cast(datetime | None, policy.active_to),
        is_active=cast(bool, policy.is_active),
        created_at=cast(datetime, policy.created_at),
        updated_at=cast(datetime, policy.updated_at),
    )


def create_asset(db: Session, body: AssetCreate, *, actor: User) -> AssetOut:
    asset = Asset(
        organisation_id=actor.organisation_id,
        asset_type=body.asset_type,
        name=body.name,
        description=body.description,
        status=body.status,
        criticality=body.criticality,
        geometry_json=body.geometry_json,
        metadata_json=body.metadata_json,
        is_active=body.is_active,
    )
    db.add(asset)
    db.flush()
    AuditService.log_event(
        db,
        action="asset.create",
        change_summary=f"Created asset {asset.name}",
        organisation_id=cast(int, actor.organisation_id),
        user_id=cast(str, actor.username),
        resource_id=str(asset.id),
        resource_type="asset",
        details={"asset_type": body.asset_type, "criticality": body.criticality},
    )
    db.commit()
    db.refresh(asset)
    return _asset_to_out(asset)


def list_assets(
    db: Session,
    *,
    user: User,
    asset_type: str | None = None,
    is_active: bool | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[AssetOut]:
    query = apply_org_filter(db.query(Asset), Asset, user)
    if asset_type:
        query = query.filter(Asset.asset_type == asset_type)
    if is_active is not None:
        query = query.filter(Asset.is_active == is_active)
    rows = query.order_by(Asset.criticality.desc(), Asset.id.desc()).offset(offset).limit(limit).all()
    return [_asset_to_out(row) for row in rows]


def get_asset(db: Session, asset_id: int, *, user: User) -> AssetOut:
    query = apply_org_filter(db.query(Asset).filter(Asset.id == asset_id), Asset, user)
    row = query.first()
    if row is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    return _asset_to_out(row)


def update_asset(db: Session, asset_id: int, body: AssetUpdate, *, actor: User) -> AssetOut:
    query = apply_org_filter(db.query(Asset).filter(Asset.id == asset_id), Asset, actor)
    row = query.first()
    if row is None:
        raise HTTPException(status_code=404, detail="Asset not found")

    changed: dict[str, dict[str, Any]] = {}
    for field in ("name", "description", "status", "criticality", "geometry_json", "metadata_json", "is_active"):
        value = getattr(body, field)
        if value is not None and value != getattr(row, field):
            changed[field] = {"from": getattr(row, field), "to": value}
            setattr(row, field, value)
    row.updated_at = _now_utc()

    if changed:
        AuditService.log_event(
            db,
            action="asset.update",
            change_summary=f"Updated asset {asset_id}",
            organisation_id=cast(int, row.organisation_id),
            user_id=cast(str, actor.username),
            resource_id=str(asset_id),
            resource_type="asset",
            details={"changes": changed},
        )

    db.commit()
    db.refresh(row)
    return _asset_to_out(row)


def create_asset_link(db: Session, asset_id: int, body: AssetLinkCreate, *, actor: User) -> AssetLinkOut:
    assets = apply_org_filter(
        db.query(Asset).filter(Asset.id.in_([asset_id, body.target_asset_id])),
        Asset,
        actor,
    ).all()
    if len(assets) != 2:
        raise HTTPException(status_code=404, detail="Asset link members must exist in scope")
    link = AssetLink(
        organisation_id=actor.organisation_id,
        source_asset_id=asset_id,
        target_asset_id=body.target_asset_id,
        relation_type=body.relation_type,
        metadata_json=body.metadata_json,
    )
    db.add(link)
    db.flush()
    AuditService.log_event(
        db,
        action="asset.link.create",
        change_summary=f"Linked asset {asset_id} to {body.target_asset_id}",
        organisation_id=cast(int, actor.organisation_id),
        user_id=cast(str, actor.username),
        resource_id=str(link.id),
        resource_type="asset_link",
        details={"relation_type": body.relation_type},
    )
    db.commit()
    db.refresh(link)
    return _link_to_out(link)


def create_asset_policy(db: Session, asset_id: int, body: AssetPolicyCreate, *, actor: User) -> AssetPolicyOut:
    asset = apply_org_filter(db.query(Asset).filter(Asset.id == asset_id), Asset, actor).first()
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    policy = AssetPolicy(
        organisation_id=actor.organisation_id,
        asset_id=asset_id,
        policy_type=body.policy_type,
        name=body.name,
        policy_json=body.policy_json,
        active_from=body.active_from,
        active_to=body.active_to,
        is_active=body.is_active,
    )
    db.add(policy)
    db.flush()
    AuditService.log_event(
        db,
        action="asset.policy.create",
        change_summary=f"Created policy for asset {asset_id}",
        organisation_id=cast(int, actor.organisation_id),
        user_id=cast(str, actor.username),
        resource_id=str(policy.id),
        resource_type="asset_policy",
        details={"policy_type": body.policy_type, "name": body.name},
    )
    db.commit()
    db.refresh(policy)
    return _policy_to_out(policy)


def list_asset_policies(db: Session, asset_id: int, *, user: User) -> list[AssetPolicyOut]:
    asset = apply_org_filter(db.query(Asset).filter(Asset.id == asset_id), Asset, user).first()
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    rows = (
        apply_org_filter(db.query(AssetPolicy).filter(AssetPolicy.asset_id == asset_id), AssetPolicy, user)
        .order_by(AssetPolicy.created_at.desc())
        .all()
    )
    return [_policy_to_out(row) for row in rows]


def asset_has_active_maintenance_window(db: Session, asset_id: int, *, at_time: datetime | None = None) -> bool:
    current_time = at_time or _now_utc()
    policy = (
        db.query(AssetPolicy)
        .filter(
            AssetPolicy.asset_id == asset_id,
            AssetPolicy.policy_type == "maintenance_window",
            AssetPolicy.is_active.is_(True),
        )
        .filter((AssetPolicy.active_from.is_(None)) | (AssetPolicy.active_from <= current_time))
        .filter((AssetPolicy.active_to.is_(None)) | (AssetPolicy.active_to >= current_time))
        .first()
    )
    return policy is not None


AssetsServiceDep = Annotated[Session, Depends(get_db)]
