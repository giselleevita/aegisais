from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class AssetCreate(BaseModel):
    asset_type: str = Field(..., description="cable_segment, landing_station, patrol_zone, sensor_node")
    name: str
    description: Optional[str] = None
    status: str = "active"
    criticality: str = "medium"
    geometry_json: dict[str, Any]
    metadata_json: Optional[dict[str, Any]] = None
    is_active: bool = True


class AssetUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    criticality: Optional[str] = None
    geometry_json: Optional[dict[str, Any]] = None
    metadata_json: Optional[dict[str, Any]] = None
    is_active: Optional[bool] = None


class AssetOut(BaseModel):
    id: int
    organisation_id: int
    asset_type: str
    name: str
    description: Optional[str] = None
    status: str
    criticality: str
    geometry_json: dict[str, Any]
    metadata_json: Optional[dict[str, Any]] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class AssetLinkCreate(BaseModel):
    target_asset_id: int
    relation_type: str = Field(..., description="attached_to, protects, adjacent_to, depends_on")
    metadata_json: Optional[dict[str, Any]] = None


class AssetLinkOut(BaseModel):
    id: int
    organisation_id: int
    source_asset_id: int
    target_asset_id: int
    relation_type: str
    metadata_json: Optional[dict[str, Any]] = None
    created_at: datetime


class AssetPolicyCreate(BaseModel):
    policy_type: str = Field(..., description="maintenance_window, traffic_threshold, escalation_rule")
    name: str
    policy_json: dict[str, Any]
    active_from: Optional[datetime] = None
    active_to: Optional[datetime] = None
    is_active: bool = True


class AssetPolicyOut(BaseModel):
    id: int
    organisation_id: int
    asset_id: int
    policy_type: str
    name: str
    policy_json: dict[str, Any]
    active_from: Optional[datetime] = None
    active_to: Optional[datetime] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
