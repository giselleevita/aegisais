"""ML-enhanced scoring engine (GAP-01).

Provides:
1. Trajectory prediction using a lightweight statistical model
   (exponential moving average of speed/heading as baseline;
   replaceable with LSTM/Transformer when training data available)
2. Ensemble scoring combining heuristic rules + statistical anomaly score
3. Explainability via feature contributions (SHAP-compatible interface)

This replaces the placeholder scoring.py with a production-grade engine.
"""

from __future__ import annotations

import logging
import math
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Optional

from app.infrastructure.ingest.loaders import AisPoint
from app.tracking.features import haversine_m, implied_speed_knots, heading_delta_deg
from app.services.llm import generate_anomaly_explanation, is_llm_enabled

_log = logging.getLogger("aegisais.detection.ml_scoring")


@dataclass
class VesselProfile:
    """Statistical profile of a vessel's normal behavior (pattern of life)."""

    mmsi: str
    speed_mean: float = 0.0
    speed_std: float = 5.0
    heading_mean: float = 0.0
    heading_std: float = 30.0
    update_interval_mean: float = 30.0  # seconds
    update_interval_std: float = 60.0
    sample_count: int = 0
    last_updated: Optional[datetime] = None

    def update(self, speed: float, heading: float, interval: float) -> None:
        """Update profile with exponential moving average (alpha=0.1)."""
        alpha = 0.1
        self.sample_count += 1

        if self.sample_count == 1:
            self.speed_mean = speed
            self.heading_mean = heading
            self.update_interval_mean = interval
            return

        # EMA update
        self.speed_mean = alpha * speed + (1 - alpha) * self.speed_mean
        self.speed_std = math.sqrt(
            alpha * (speed - self.speed_mean) ** 2 + (1 - alpha) * self.speed_std ** 2
        )
        self.heading_mean = alpha * heading + (1 - alpha) * self.heading_mean
        self.heading_std = math.sqrt(
            alpha * (heading - self.heading_mean) ** 2 + (1 - alpha) * self.heading_std ** 2
        )
        self.update_interval_mean = alpha * interval + (1 - alpha) * self.update_interval_mean
        self.update_interval_std = math.sqrt(
            alpha * (interval - self.update_interval_mean) ** 2
            + (1 - alpha) * self.update_interval_std ** 2
        )


# In-memory profile store (per-process; Redis-backed version for multi-pod planned)
_profiles: dict[str, VesselProfile] = {}


def get_or_create_profile(mmsi: str) -> VesselProfile:
    if mmsi not in _profiles:
        _profiles[mmsi] = VesselProfile(mmsi=mmsi)
    return _profiles[mmsi]


def predict_next_position(
    track: list[AisPoint],
) -> Optional[dict[str, float]]:
    """Predict next position based on recent track using linear extrapolation.

    Returns predicted lat, lon, sog, cog based on last 3-5 points.
    This is the baseline predictor; replace with LSTM when training data available.
    """
    if len(track) < 2:
        return None

    # Use last 2 points for linear extrapolation
    p1, p2 = track[-2], track[-1]
    dt = (p2.timestamp - p1.timestamp).total_seconds()
    if dt <= 0:
        return None

    # Speed and heading from latest
    speed_kn = p2.sog if p2.sog is not None else (implied_speed_knots(p1, p2) or 0)
    cog = p2.cog if p2.cog is not None else 0

    # Extrapolate position forward by dt seconds
    speed_ms = speed_kn * 0.514444  # knots to m/s
    dist_m = speed_ms * dt

    cog_rad = math.radians(cog)
    dlat = (dist_m * math.cos(cog_rad)) / 111_320
    dlon = (dist_m * math.sin(cog_rad)) / (111_320 * max(math.cos(math.radians(p2.lat)), 0.01))

    return {
        "predicted_lat": p2.lat + dlat,
        "predicted_lon": p2.lon + dlon,
        "predicted_sog": speed_kn,
        "predicted_cog": cog,
        "confidence": min(0.95, 0.5 + 0.1 * min(len(track), 5)),
    }


def compute_anomaly_score(
    point: AisPoint,
    track: list[AisPoint],
) -> dict[str, Any]:
    """Compute statistical anomaly score for a single AIS point.

    Returns:
        score: 0-100 anomaly score
        features: dict of feature contributions (SHAP-style)
        prediction: predicted position vs actual
    """
    profile = get_or_create_profile(point.mmsi)
    features: dict[str, float] = {}
    total_anomaly = 0.0

    # Feature 1: Speed deviation from profile
    speed = point.sog or 0
    if profile.speed_std > 0 and profile.sample_count > 5:
        speed_z = abs(speed - profile.speed_mean) / max(profile.speed_std, 0.1)
        features["speed_deviation"] = min(speed_z * 15, 30)
        total_anomaly += features["speed_deviation"]
    else:
        features["speed_deviation"] = 0

    # Feature 2: Position prediction error
    prediction = predict_next_position(track)
    if prediction and len(track) >= 2:
        pred_dist = haversine_m(
            point.lat, point.lon,
            prediction["predicted_lat"], prediction["predicted_lon"],
        )
        # Normalize: >5km deviation is highly anomalous
        features["position_prediction_error"] = min(pred_dist / 5000 * 30, 30)
        total_anomaly += features["position_prediction_error"]
    else:
        features["position_prediction_error"] = 0

    # Feature 3: Update interval anomaly
    if len(track) >= 2:
        dt = (point.timestamp - track[-2].timestamp).total_seconds()
        if profile.update_interval_std > 0 and profile.sample_count > 5:
            interval_z = abs(dt - profile.update_interval_mean) / max(profile.update_interval_std, 1)
            features["interval_anomaly"] = min(interval_z * 10, 20)
            total_anomaly += features["interval_anomaly"]
        else:
            features["interval_anomaly"] = 0

        # Update profile
        heading = point.cog or point.heading or 0
        profile.update(speed, heading, dt)
        profile.last_updated = point.timestamp
    else:
        features["interval_anomaly"] = 0

    # Feature 4: Heading consistency
    if len(track) >= 2 and point.cog is not None and track[-2].cog is not None:
        heading_change = heading_delta_deg(track[-2].cog, point.cog)
        dt = (point.timestamp - track[-2].timestamp).total_seconds()
        if dt > 0:
            rate = heading_change / dt
            features["heading_rate"] = min(rate * 5, 20)
            total_anomaly += features["heading_rate"]
        else:
            features["heading_rate"] = 0
    else:
        features["heading_rate"] = 0

    score = min(100, int(total_anomaly))

    return {
        "anomaly_score": score,
        "features": features,
        "prediction": prediction,
        "profile_sample_count": profile.sample_count,
    }


def ensemble_score(
    rule_alerts: list[dict[str, Any]],
    ml_score: dict[str, Any],
    weights: Optional[dict[str, float]] = None,
) -> dict[str, Any]:
    """Combine heuristic rule alerts with ML anomaly score.

    Default weights:
    - Rule-based severity: 0.6 (trusted, explainable)
    - ML anomaly score: 0.4 (novel detection capability)

    Returns composite score with explainability breakdown.
    """
    w = weights or {"rules": 0.6, "ml": 0.4}

    # Max rule severity
    max_rule_severity = max((a["severity"] for a in rule_alerts), default=0)

    # ML score
    ml_anomaly = ml_score.get("anomaly_score", 0)

    composite = int(w["rules"] * max_rule_severity + w["ml"] * ml_anomaly)
    composite = min(100, max(0, composite))

    # Build explanation
    contributions = []
    if rule_alerts:
        for alert in rule_alerts:
            contributions.append({
                "source": "rule",
                "type": alert["type"],
                "severity": alert["severity"],
                "weight": w["rules"],
                "contribution": round(w["rules"] * alert["severity"], 1),
            })

    contributions.append({
        "source": "ml",
        "type": "statistical_anomaly",
        "severity": ml_anomaly,
        "weight": w["ml"],
        "contribution": round(w["ml"] * ml_anomaly, 1),
        "features": ml_score.get("features", {}),
    })

    return {
        "composite_score": composite,
        "rule_score": max_rule_severity,
        "ml_score": ml_anomaly,
        "contributions": contributions,
        "explainability": {
            "method": "weighted_ensemble",
            "weights": w,
            "rule_count": len(rule_alerts),
            "ml_features": list(ml_score.get("features", {}).keys()),
        },
    }


async def enrich_ensemble_with_narrative(
    result: dict[str, Any],
    mmsi: Optional[str] = None,
) -> dict[str, Any]:
    """Add an LLM-generated explanation narrative to an ensemble_score result.

    Call this at the API layer (after ensemble_score) to avoid making the
    synchronous detection pipeline depend on async I/O.
    """
    if not is_llm_enabled():
        return result

    narrative = await generate_anomaly_explanation(
        composite_score=result["composite_score"],
        rule_score=result["rule_score"],
        ml_score=result["ml_score"],
        contributions=result["contributions"],
        mmsi=mmsi,
    )
    if narrative:
        result["explanation_narrative"] = narrative
    return result
