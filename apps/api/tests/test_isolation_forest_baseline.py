from datetime import datetime, timedelta, timezone
import hashlib
import json

from app.detection.isolation_forest import FEATURE_NAMES, IsolationForestScorer, extract_trajectory_features
from app.infrastructure.ingest.loaders import AisPoint


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
