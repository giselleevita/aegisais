from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Asset(Base):
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    organisation_id = Column(
        Integer,
        ForeignKey("organisations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    asset_type = Column(String(32), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(32), nullable=False, default="active", index=True)
    criticality = Column(String(16), nullable=False, default="medium", index=True)
    geometry_json = Column(JSON, nullable=False)
    metadata_json = Column(JSON, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=_utcnow,
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=_utcnow,
        onupdate=_utcnow,
    )


Index("idx_assets_org_type_active", Asset.organisation_id, Asset.asset_type, Asset.is_active)
Index("idx_assets_org_criticality", Asset.organisation_id, Asset.criticality)


class AssetLink(Base):
    __tablename__ = "asset_links"
    __table_args__ = (
        UniqueConstraint(
            "source_asset_id",
            "target_asset_id",
            "relation_type",
            name="uq_asset_links_directional_relation",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    organisation_id = Column(
        Integer,
        ForeignKey("organisations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    source_asset_id = Column(
        Integer,
        ForeignKey("assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_asset_id = Column(
        Integer,
        ForeignKey("assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    relation_type = Column(String(32), nullable=False, index=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=_utcnow,
    )


Index("idx_asset_links_org_source", AssetLink.organisation_id, AssetLink.source_asset_id)
Index("idx_asset_links_org_target", AssetLink.organisation_id, AssetLink.target_asset_id)


class AssetPolicy(Base):
    __tablename__ = "asset_policies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    organisation_id = Column(
        Integer,
        ForeignKey("organisations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    asset_id = Column(
        Integer,
        ForeignKey("assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    policy_type = Column(String(32), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    policy_json = Column(JSON, nullable=False)
    active_from = Column(DateTime(timezone=True), nullable=True, index=True)
    active_to = Column(DateTime(timezone=True), nullable=True, index=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=_utcnow,
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=_utcnow,
        onupdate=_utcnow,
    )


Index("idx_asset_policies_org_asset_type", AssetPolicy.organisation_id, AssetPolicy.asset_id, AssetPolicy.policy_type)
