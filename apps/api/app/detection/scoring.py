"""Scoring module — thin bridge to ML ensemble scoring (GAP-01).

The ensemble_score function combines heuristic rule outputs with
statistical anomaly detection.  See ml_scoring.py for implementation.
"""

from app.detection.ml_scoring import (  # noqa: F401
    compute_anomaly_score,
    ensemble_score,
    predict_next_position,
    VesselProfile,
)
