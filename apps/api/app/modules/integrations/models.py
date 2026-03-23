"""Integration reference tables (PostGIS-friendly storage path)."""

from sqlalchemy import Column, DateTime, Float, JSON, String, func

from app.core.database import Base


class PortReference(Base):
    __tablename__ = "port_references"

    source = Column(String(64), primary_key=True)
    source_id = Column(String(128), primary_key=True)
    name = Column(String(255), nullable=False, index=True)
    country_code = Column(String(8), nullable=True, index=True)
    unlocode = Column(String(16), nullable=True, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    # PostGIS-friendly ingestion path: write POINT(lon lat) then cast to geometry in migration/ETL.
    geom_wkt = Column(String(64), nullable=False)
    metadata_json = Column(JSON, nullable=True)
    license_tag = Column(String(64), nullable=False, default="restricted_non_commercial")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class UnlocodeReference(Base):
    __tablename__ = "unlocode_references"

    unlocode = Column(String(16), primary_key=True)
    name = Column(String(255), nullable=False, index=True)
    country_code = Column(String(8), nullable=True, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    geom_wkt = Column(String(64), nullable=False)
    metadata_json = Column(JSON, nullable=True)
    license_tag = Column(String(64), nullable=False, default="restricted_non_commercial")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

