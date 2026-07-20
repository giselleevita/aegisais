"""Versioned Isolation Forest baseline for trajectory-window anomaly scoring."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, pstdev
from typing import Any

from app.core.config import settings
from app.infrastructure.ingest.loaders import AisPoint
from app.modules.fusion.fused_rules import nearest_cable_segment
from app.tracking.features import haversine_m, heading_delta_deg, implied_speed_knots

FEATURE_NAMES = [
    "speed_knots",
    "speed_std",
    "acceleration_knots_per_sec",
    "turn_rate_deg_per_sec",
    "course_entropy",
    "displacement_m",
    "loiter_ratio",
    "update_gap_sec",
    "prediction_residual_m",
    "distance_to_cable_m",
]


@dataclass(frozen=True)
class ModelStatus:
    state: str
    model_version: str | None
    reason: str | None
    feature_schema: list[str]
    trained_at: str | None = None
    dataset_hash: str | None = None
    metrics: dict[str, Any] | None = None


def extract_trajectory_features(track: list[AisPoint]) -> dict[str, float]:
    if not track:
        raise ValueError("A trajectory window requires at least one point")
    points = sorted(track, key=lambda item: item.timestamp)
    current = points[-1]
    speeds = [float(item.sog or 0.0) for item in points]
    dt = max(0.0, (points[-1].timestamp - points[-2].timestamp).total_seconds()) if len(points) >= 2 else 0.0
    acceleration = (speeds[-1] - speeds[-2]) / dt if len(points) >= 2 and dt > 0 else 0.0
    turn_rate = 0.0
    if len(points) >= 2 and dt > 0:
        previous_course = points[-2].cog if points[-2].cog is not None else points[-2].heading
        current_course = current.cog if current.cog is not None else current.heading
        if previous_course is not None and current_course is not None:
            turn_rate = heading_delta_deg(previous_course, current_course) / dt

    courses = [item.cog for item in points if item.cog is not None]
    course_entropy = _circular_entropy(courses)
    displacement = haversine_m(points[0].lat, points[0].lon, current.lat, current.lon) if len(points) >= 2 else 0.0
    path_distance = sum(
        haversine_m(a.lat, a.lon, b.lat, b.lon) for a, b in zip(points, points[1:])
    )
    loiter_ratio = 0.0 if path_distance <= 1.0 else max(0.0, min(1.0, 1.0 - displacement / path_distance))

    prediction_residual = 0.0
    if len(points) >= 3:
        p1, p2 = points[-3], points[-2]
        prior_dt = (p2.timestamp - p1.timestamp).total_seconds()
        if prior_dt > 0 and dt > 0:
            speed = p2.sog if p2.sog is not None else (implied_speed_knots(p1, p2) or 0.0)
            course = p2.cog if p2.cog is not None else 0.0
            distance = speed * 0.514444 * dt
            course_rad = math.radians(course)
            predicted_lat = p2.lat + distance * math.cos(course_rad) / 111_320
            predicted_lon = p2.lon + distance * math.sin(course_rad) / (
                111_320 * max(math.cos(math.radians(p2.lat)), 0.01)
            )
            prediction_residual = haversine_m(current.lat, current.lon, predicted_lat, predicted_lon)

    _, cable_distance = nearest_cable_segment(current.lat, current.lon)
    return {
        "speed_knots": speeds[-1],
        "speed_std": pstdev(speeds) if len(speeds) > 1 else 0.0,
        "acceleration_knots_per_sec": abs(acceleration),
        "turn_rate_deg_per_sec": abs(turn_rate),
        "course_entropy": course_entropy,
        "displacement_m": displacement,
        "loiter_ratio": loiter_ratio,
        "update_gap_sec": dt,
        "prediction_residual_m": prediction_residual,
        "distance_to_cable_m": cable_distance,
    }


def _circular_entropy(courses: list[float], bins: int = 8) -> float:
    if len(courses) < 2:
        return 0.0
    counts = [0] * bins
    for course in courses:
        counts[int((course % 360) / 360 * bins) % bins] += 1
    probabilities = [count / len(courses) for count in counts if count]
    return -sum(value * math.log(value) for value in probabilities) / math.log(bins)


class IsolationForestScorer:
    def __init__(self, model_path: str | Path | None = None, manifest_path: str | Path | None = None):
        self.model_path = Path(model_path or settings.ML_MODEL_PATH)
        self.manifest_path = Path(manifest_path or settings.ML_MODEL_MANIFEST_PATH)
        self._model = None
        self._manifest: dict[str, Any] | None = None
        self._error: str | None = None

    def _load(self) -> None:
        if self._model is not None or self._error is not None:
            return
        if not self.model_path.exists() or not self.manifest_path.exists():
            self._error = "model_artifact_missing"
            return
        try:
            import joblib  # type: ignore[import-untyped]

            manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
            if manifest.get("feature_schema") != FEATURE_NAMES:
                raise ValueError("feature_schema_mismatch")
            model_bytes = self.model_path.read_bytes()
            if hashlib.sha256(model_bytes).hexdigest() != manifest.get("artifact_sha256"):
                raise ValueError("artifact_hash_mismatch")
            self._model = joblib.load(self.model_path)
            self._manifest = manifest
        except Exception as exc:
            self._error = str(exc)

    def status(self) -> ModelStatus:
        self._load()
        if self._model is None or self._manifest is None:
            return ModelStatus("degraded", None, self._error or "model_unavailable", FEATURE_NAMES)
        return ModelStatus(
            "ready",
            self._manifest.get("model_version"),
            None,
            FEATURE_NAMES,
            self._manifest.get("trained_at"),
            self._manifest.get("dataset_sha256"),
            self._manifest.get("metrics"),
        )

    def score(self, track: list[AisPoint]) -> dict[str, Any]:
        features = extract_trajectory_features(track)
        self._load()
        if self._model is None or self._manifest is None:
            return {
                "state": "degraded",
                "reason": self._error or "model_unavailable",
                "anomaly_percentile": None,
                "features": features,
            }
        vector = [[features[name] for name in FEATURE_NAMES]]
        raw_score = float(-self._model.score_samples(vector)[0])
        calibration = sorted(float(item) for item in self._manifest.get("calibration_scores", []))
        percentile = 100.0 * sum(item <= raw_score for item in calibration) / max(len(calibration), 1)
        threshold = float(self._manifest.get("threshold_percentile", 95.0))
        return {
            "state": "ready",
            "model_version": self._manifest.get("model_version"),
            "raw_score": raw_score,
            "anomaly_percentile": round(percentile, 2),
            "is_anomaly": percentile >= threshold,
            "threshold_percentile": threshold,
            "features": features,
            "explanation": _feature_explanation(features, self._manifest),
        }


def train_isolation_forest(
    feature_rows: list[dict[str, float]],
    *,
    model_path: str | Path,
    manifest_path: str | Path,
    dataset_bytes: bytes,
    metrics: dict[str, Any] | None = None,
    random_state: int = 42,
    trained_at: str | None = None,
) -> dict[str, Any]:
    if len(feature_rows) < 20:
        raise ValueError("At least 20 normal trajectory windows are required")
    import joblib  # type: ignore[import-untyped]
    import sklearn  # type: ignore[import-untyped]
    from sklearn.ensemble import IsolationForest  # type: ignore[import-untyped]

    matrix = [[row[name] for name in FEATURE_NAMES] for row in feature_rows]
    model = IsolationForest(
        n_estimators=200,
        contamination="auto",
        random_state=random_state,
        n_jobs=1,
    )
    model.fit(matrix)
    calibration_scores = sorted(float(-value) for value in model.score_samples(matrix))
    feature_stats = {
        name: {"mean": mean(row[name] for row in feature_rows), "std": pstdev(row[name] for row in feature_rows)}
        for name in FEATURE_NAMES
    }
    model_path = Path(model_path)
    manifest_path = Path(manifest_path)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, model_path, compress=3)
    artifact_hash = hashlib.sha256(model_path.read_bytes()).hexdigest()
    manifest = {
        "model_version": f"isolation-forest-{datetime.now(timezone.utc).strftime('%Y%m%d')}",
        "model_type": "sklearn.ensemble.IsolationForest",
        "sklearn_version": sklearn.__version__,
        "trained_at": trained_at or datetime.now(timezone.utc).isoformat(),
        "random_state": random_state,
        "feature_schema": FEATURE_NAMES,
        "dataset_sha256": hashlib.sha256(dataset_bytes).hexdigest(),
        "artifact_sha256": artifact_hash,
        "threshold_percentile": 95.0,
        "calibration_scores": calibration_scores,
        "feature_stats": feature_stats,
        "metrics": metrics or {},
        "score_semantics": "empirical percentile, not probability",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def _feature_explanation(features: dict[str, float], manifest: dict[str, Any]) -> list[dict[str, Any]]:
    contributions: list[dict[str, Any]] = []
    for name, value in features.items():
        stats = (manifest.get("feature_stats") or {}).get(name) or {}
        std = float(stats.get("std") or 0.0)
        deviation = abs(value - float(stats.get("mean") or 0.0)) / std if std > 1e-9 else 0.0
        contributions.append({"feature": name, "value": round(value, 4), "standardDeviations": round(deviation, 2)})
    return sorted(contributions, key=lambda item: item["standardDeviations"], reverse=True)[:5]


default_scorer = IsolationForestScorer()
