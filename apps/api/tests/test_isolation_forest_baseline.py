from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path

import pytest

from app.detection.isolation_forest import FEATURE_NAMES, IsolationForestScorer, extract_trajectory_features
from app.infrastructure.ingest.loaders import AisPoint
from scripts.train_isolation_forest import load_windows


DATASET_PATH = Path(__file__).resolve().parents[3] / "data/training/festival_trajectory_baseline.json"
MANIFEST_PATH = Path(__file__).resolve().parents[3] / "data/models/isolation_forest.manifest.json"


def test_feature_extractor_is_complete_and_finite():
    base = datetime(2026, 8, 20, tzinfo=timezone.utc)
    track = [
        AisPoint("211000001", base, 59.3, 24.1, 12.0, 70.0, 70.0),
        AisPoint("211000001", base + timedelta(minutes=5), 59.32, 24.2, 12.2, 70.0, 70.0),
        AisPoint("211000001", base + timedelta(minutes=10), 59.34, 24.3, 12.1, 72.0, 71.0),
    ]
    features = extract_trajectory_features(track)
    assert list(features) == FEATURE_NAMES
    assert features["update_gap_sec"] == 300
    assert features["displacement_m"] > 0
    assert features["distance_to_cable_m"] >= 0


def test_missing_model_is_explicitly_degraded(tmp_path):
    scorer = IsolationForestScorer(tmp_path / "missing.joblib", tmp_path / "missing.json")
    status = scorer.status()
    assert status.state == "degraded"
    assert status.reason == "model_artifact_missing"


def test_incompatible_or_tampered_model_is_explicitly_degraded(tmp_path):
    artifact = tmp_path / "model.joblib"
    manifest = tmp_path / "model.json"
    artifact.write_bytes(b"not-a-real-model")
    manifest.write_text(
        json.dumps(
            {
                "feature_schema": ["wrong_feature"],
                "artifact_sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
            }
        ),
        encoding="utf-8",
    )
    incompatible = IsolationForestScorer(artifact, manifest).status()
    assert incompatible.state == "degraded"
    assert incompatible.reason == "feature_schema_mismatch"

    manifest.write_text(
        json.dumps({"feature_schema": FEATURE_NAMES, "artifact_sha256": "0" * 64}),
        encoding="utf-8",
    )
    tampered = IsolationForestScorer(artifact, manifest).status()
    assert tampered.state == "degraded"
    assert tampered.reason == "artifact_hash_mismatch"


def test_festival_training_splits_are_disjoint_and_large_enough():
    rows, normal, anomalies, vessel_hours, _, split = load_windows(DATASET_PATH)
    assert len(rows) >= 20
    assert normal
    assert anomalies
    assert vessel_hours >= 120
    assert split["training_vessels"] == 16
    assert split["validation_normal_vessels"] == 10
    assert split["validation_anomaly_vessels"] == 12
    assert len(split["vessel_classes"]) >= 2
    assert split["validation_time_start"] > split["training_time_end"]


def test_training_rejects_insufficient_validation_hours(tmp_path):
    payload = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    payload["vessels"] = [
        vessel
        for vessel in payload["vessels"]
        if vessel["split"] == "train" or vessel["behavior"] != "normal_transit"
    ]
    invalid = tmp_path / "insufficient-hours.json"
    invalid.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="100 held-out normal vessel-hours"):
        load_windows(invalid)


def test_committed_model_manifest_meets_synthetic_acceptance_thresholds():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    metrics = manifest["metrics"]
    assert metrics["normal_vessel_hours"] >= 100
    assert metrics["synthetic_recall"] >= 0.8
    assert metrics["false_alerts_per_100_vessel_hours"] <= 1.0
    assert metrics["real_world_precision"] == "not_established"
    assert "MMSI-separated" in metrics["split_policy"]
    assert manifest["threshold_percentile"] == 95.0
