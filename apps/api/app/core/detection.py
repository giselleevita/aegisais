"""Anomaly detection tuning configuration for AegisAIS.

Provides per-detection-type thresholds that operators can override via the
``AEGISAIS_DETECTION_*`` environment variables. A single cached instance is
returned by ``get_detection_config()``.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DetectionConfig(BaseSettings):
    """Tunable thresholds for each S-AIS anomaly detector.

    All speed values are in knots; heading/course in degrees; gap durations
    in seconds.  Score thresholds are normalised to [0, 1] or [0, 100]
    depending on the detector (see inline docs).
    """

    model_config = SettingsConfigDict(
        env_prefix="AEGISAIS_DETECTION_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---- Teleportation / position jump -----
    teleport_max_distance_nm: float = Field(
        default=50.0,
        ge=0.1,
        le=500.0,
        description="Maximum plausible position jump (nautical miles) for a single AIS update.",
    )
    teleport_max_speed_knots: float = Field(
        default=40.0,
        ge=1.0,
        le=100.0,
        description="Max physically plausible speed (knots); jumps implying faster movement flag as teleport.",
    )

    # ---- Dark period / AIS gap -----
    dark_gap_threshold_seconds: int = Field(
        default=3_600,
        ge=60,
        le=86_400,
        description="Minimum gap (seconds) between last and next AIS message to raise a DARK_PERIOD alert.",
    )
    dark_gap_high_risk_seconds: int = Field(
        default=21_600,
        ge=3_600,
        le=172_800,
        description="Gap (seconds) above which the alert severity escalates to high-risk.",
    )

    # ---- Abnormal turn rate -----
    turn_rate_max_deg_per_min: float = Field(
        default=720.0,
        ge=10.0,
        le=3_600.0,
        description="Maximum turning rate (degrees/minute); exceeding this triggers a TURN_RATE alert.",
    )

    # ---- Speed anomaly -----
    speed_anomaly_max_knots: float = Field(
        default=35.0,
        ge=1.0,
        le=100.0,
        description="Maximum reported speed (SOG knots) before raising a SPEED_ANOMALY alert.",
    )

    # ---- Spoofing confidence -----
    spoofing_min_confidence: float = Field(
        default=0.65,
        ge=0.0,
        le=1.0,
        description="Minimum model confidence score to emit a SPOOFING_SUSPECTED alert.",
    )

    # ---- Geofence -----
    geofence_buffer_nm: float = Field(
        default=0.5,
        ge=0.0,
        le=10.0,
        description="Buffer around geofence polygons (nautical miles) to avoid boundary noise.",
    )

    # ---- Global severity weighting -----
    severity_scale_factor: float = Field(
        default=1.0,
        ge=0.1,
        le=5.0,
        description="Multiplier applied to all raw severity scores (useful for region-specific tuning).",
    )


@lru_cache(maxsize=1)
def get_detection_config() -> DetectionConfig:
    """Return the singleton detection configuration (cached after first call)."""
    return DetectionConfig()
