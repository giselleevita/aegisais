import hashlib
import json
from datetime import timezone

from sqlalchemy import Column, ForeignKey, Integer, String, DateTime, JSON, Index
from app.core.database import Base


def _normalise_ts(ts) -> str:
    """Truncate to minute bucket and normalise to UTC ISO string.

    Strips seconds and sub-seconds so that small timestamp drift (e.g. float
    precision, different ISO serialisation) maps to the same key bucket.
    """
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    else:
        import datetime as _dt
        ts = ts.astimezone(_dt.timezone.utc)
    return ts.strftime("%Y-%m-%dT%H:%MZ")


def derive_evidence_hash(evidence: dict) -> str:
    """Stable SHA-256 fingerprint of the slim evidence payload (BL-009).

    Keys are sorted and non-serialisable values are coerced via ``default=str``
    so the hash is deterministic across Python versions and dict ordering.
    """
    canonical = json.dumps(evidence, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


def derive_alert_idempotency_key(
    organisation_id: int,
    mmsi: str,
    alert_type: str,
    timestamp,
) -> str:
    """Canonical idempotency key for an alert (BL-003).

    Key material: ``{org_id}:{mmsi}:{type}:{minute_bucket_utc}``

    Minute-level bucketing absorbs sub-second timestamp drift and different
    ISO-8601 serialisation formats while still giving per-rule, per-vessel,
    per-minute uniqueness.  The key is stored on the Alert row so operators
    can reproduce the derivation from the record alone.
    """
    key_material = f"{organisation_id}:{mmsi}:{alert_type}:{_normalise_ts(timestamp)}"
    return hashlib.sha256(key_material.encode()).hexdigest()


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    organisation_id = Column(
        Integer,
        ForeignKey("organisations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="SET NULL"), nullable=True, index=True)
    source_device_id = Column(Integer, ForeignKey("iot_devices.id", ondelete="SET NULL"), nullable=True, index=True)
    timestamp = Column(DateTime, index=True, nullable=False)
    mmsi = Column(String, index=True, nullable=False)

    type = Column(String, index=True, nullable=False)
    severity = Column(Integer, index=True, nullable=False)

    summary = Column(String, nullable=False)
    evidence = Column(JSON, nullable=False)

    # BL-003: constraint-backed deduplication key.
    # Derived from (org_id, mmsi, type, minute-bucket UTC timestamp).
    # NULL allowed on legacy rows created before this column was added.
    idempotency_key = Column(String, nullable=True, unique=True, index=True)

    # BL-009: immutable SHA-256 fingerprint of the slim evidence payload.
    # Enables analysts to verify evidence has not been tampered with and
    # to correlate equivalent detections across time windows.
    # NULL on legacy rows that pre-date this column.
    evidence_hash = Column(String(64), nullable=True, index=True)

    # Alert management fields
    status = Column(String, default="new", nullable=False, index=True)  # new, reviewed, resolved, false_positive
    notes = Column(String, nullable=True)  # User notes/comments

class AlertCooldown(Base):
    """Tracks last alert time per (MMSI, rule_type) for cooldown mechanism."""
    __tablename__ = "alert_cooldowns"

    mmsi = Column(String, primary_key=True, nullable=False)
    rule_type = Column(String, primary_key=True, nullable=False)
    last_alert_timestamp = Column(DateTime, nullable=False, index=True)

# Composite indexes
Index("idx_alerts_mmsi_time", Alert.mmsi, Alert.timestamp)
Index("idx_alerts_org_asset_time", Alert.organisation_id, Alert.asset_id, Alert.timestamp)
Index("idx_alerts_type_time", Alert.type, Alert.timestamp)
Index("idx_alerts_severity_time", Alert.severity, Alert.timestamp)
Index("idx_alerts_timestamp", Alert.timestamp)
Index("idx_alerts_severity", Alert.severity)
Index("idx_cooldown_mmsi_type", AlertCooldown.mmsi, AlertCooldown.rule_type)
Index("idx_cooldown_timestamp", AlertCooldown.last_alert_timestamp)
