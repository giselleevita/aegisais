#!/usr/bin/env python3
"""Train the festival Isolation Forest from a labeled scenario JSON file."""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.detection.isolation_forest import extract_trajectory_features, train_isolation_forest  # noqa: E402
from app.infrastructure.ingest.loaders import AisPoint  # noqa: E402


def load_windows(path: Path) -> tuple[list[dict[str, float]], list[dict[str, float]], list[dict[str, float]], float, bytes]:
    raw = path.read_bytes()
    payload = json.loads(raw)
    feature_rows: list[dict[str, float]] = []
    normal_validation: list[dict[str, float]] = []
    anomaly_validation: list[dict[str, float]] = []
    normal_vessel_hours = 0.0
    for vessel in payload.get("vessels", []):
        track = [
            AisPoint(
                mmsi=str(vessel["mmsi"]),
                timestamp=datetime.fromisoformat(row["ts"].replace("Z", "+00:00")),
                lat=float(row["lat"]),
                lon=float(row["lon"]),
                sog=float(row["sog"]) if row.get("sog") is not None else None,
                cog=float(row["cog"]) if row.get("cog") is not None else None,
                heading=float(row["heading"]) if row.get("heading") is not None else None,
            )
            for row in vessel.get("track", [])
        ]
        target = normal_validation if vessel.get("behavior") == "normal_transit" else anomaly_validation
        for size in range(2, len(track) + 1):
            target.append(extract_trajectory_features(track[:size]))
        if vessel.get("behavior") == "normal_transit" and len(track) >= 2:
            normal_vessel_hours += (track[-1].timestamp - track[0].timestamp).total_seconds() / 3600
    # Deterministic augmentation changes only timing/speed. The exact original
    # windows remain held out for evaluation rather than leaking into training.
    for factor in (0.82, 0.88, 0.94, 1.06, 1.12, 1.18, 1.24):
        for row in normal_validation:
            augmented = dict(row)
            augmented["speed_knots"] *= factor
            augmented["update_gap_sec"] *= 2.0 - factor
            feature_rows.append(augmented)
    return feature_rows, normal_validation, anomaly_validation, normal_vessel_hours, raw


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    rows, normal_validation, anomaly_validation, normal_vessel_hours, dataset_bytes = load_windows(args.input)
    manifest = train_isolation_forest(
        rows,
        model_path=args.model,
        manifest_path=args.manifest,
        dataset_bytes=dataset_bytes,
        metrics={},
    )
    import joblib
    model = joblib.load(args.model)
    calibration = manifest["calibration_scores"]
    threshold_index = max(0, math.ceil(manifest["threshold_percentile"] / 100 * len(calibration)) - 1)
    threshold = calibration[threshold_index]

    def predicted(rows):
        matrix = [[row[name] for name in manifest["feature_schema"]] for row in rows]
        return [float(-score) >= threshold for score in model.score_samples(matrix)] if matrix else []

    anomaly_predictions = predicted(anomaly_validation)
    normal_predictions = predicted(normal_validation)
    recall = sum(anomaly_predictions) / max(len(anomaly_predictions), 1)
    false_alerts = sum(normal_predictions)
    false_alerts_per_100_hours = false_alerts / max(normal_vessel_hours, 1e-9) * 100
    manifest["metrics"] = {
        "validation": "synthetic_demo_baseline_only",
        "real_world_precision": "not_established",
        "training_windows": len(rows),
        "validation_anomaly_windows": len(anomaly_validation),
        "validation_normal_windows": len(normal_validation),
        "synthetic_recall": round(recall, 4),
        "false_alerts_per_100_vessel_hours": round(false_alerts_per_100_hours, 4),
        "normal_vessel_hours": round(normal_vessel_hours, 4),
        "split_policy": "exact normal windows held out; deterministic speed/time augmentations used for training",
    }
    manifest["applicability"] = {
        "scope": "global_fallback",
        "region": "Baltic demonstration corridor",
        "vessel_class": "all",
        "limitation": "insufficient public labeled data for per-class or cross-region validation",
    }
    args.manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if recall < 0.8 or false_alerts_per_100_hours > 1.0:
        raise SystemExit(
            f"Synthetic acceptance threshold failed: recall={recall:.3f}, "
            f"false_alerts_per_100_vessel_hours={false_alerts_per_100_hours:.3f}"
        )
    print(json.dumps({"model_version": manifest["model_version"], "training_windows": len(rows)}))


if __name__ == "__main__":
    main()
