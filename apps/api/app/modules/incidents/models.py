from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Index

from app.core.database import Base


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    organisation_id = Column(
        Integer,
        ForeignKey("organisations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    alert_id = Column(
        Integer,
        ForeignKey("alerts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        unique=True,
    )
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime, nullable=False, index=True)
    status = Column(String, nullable=False, default="open", index=True)
    title = Column(String, nullable=False)
    evidence_bundle = Column(JSON, nullable=False)


Index("idx_incidents_org_created", Incident.organisation_id, Incident.created_at)
Index("idx_incidents_org_asset", Incident.organisation_id, Incident.asset_id)
