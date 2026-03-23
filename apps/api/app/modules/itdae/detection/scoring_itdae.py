"""
ITDAE risk scoring.

Combines multiple ITDAE alert signals for a given vessel into a
composite risk score (0–100) using a weighted multi-signal approach.

Design:
  - Each active alert type contributes a weighted component score
  - GEOFENCE_ENTRY and LOITER_IN_ZONE are dominant signals
  - AIS_DARK_IN_ZONE is high weight (intent to conceal)
  - SLOW_TRANSIT_ZONE is a lower-weight supporting signal
  - Scores are capped and saturate at 100

Usage:
    from app.modules.itdae.detection.scoring_itdae import compute_vessel_risk
    risk = compute_vessel_risk(alerts_for_vessel)
"""
from typing import Any

# Weights for each alert type — must sum conceptually to 100 at max
_ALERT_WEIGHTS: dict[str, float] = {
    "LOITER_IN_ZONE":    0.40,   # Most suspicious on-station behaviour
    "AIS_DARK_IN_ZONE":  0.30,   # Intent to conceal
    "GEOFENCE_ENTRY":    0.20,   # Proximity — necessary but not sufficient alone
    "SLOW_TRANSIT_ZONE": 0.10,   # Supporting signal
}

# Severity band contributions — raw alert severity scaled into 0–1 range
def _normalise_severity(severity: int) -> float:
    return min(1.0, max(0.0, severity / 100.0))


def compute_vessel_risk(alerts: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Compute composite ITDAE risk score for a vessel given its recent alerts.

    Args:
        alerts: List of ITDAE alert dicts (type, severity, evidence fields)

    Returns:
        dict with:
          - score (int 0–100): composite risk score
          - label (str): 'critical' | 'high' | 'medium' | 'low'
          - dominant_signal (Optional[str]): highest contributing alert type
          - signal_breakdown (dict): per-type weighted contributions
    """
    if not alerts:
        return {"score": 0, "label": "low", "dominant_signal": None, "signal_breakdown": {}}

    # Gather per-type max severity (one vessel may have multiple alerts of same type)
    type_max_severity: dict[str, int] = {}
    for alert in alerts:
        atype = alert.get("type", "")
        sev = alert.get("severity", 0)
        if atype in _ALERT_WEIGHTS:
            type_max_severity[atype] = max(type_max_severity.get(atype, 0), sev)

    # Compute weighted contributions
    signal_breakdown: dict[str, float] = {}
    total = 0.0
    for atype, weight in _ALERT_WEIGHTS.items():
        if atype in type_max_severity:
            contribution = weight * _normalise_severity(type_max_severity[atype]) * 100
            signal_breakdown[atype] = round(contribution, 1)
            total += contribution

    score = min(100, round(total))

    # Label
    if score >= 80:
        label = "critical"
    elif score >= 55:
        label = "high"
    elif score >= 30:
        label = "medium"
    else:
        label = "low"

    # Dominant signal = highest contributing type
    dominant_signal = (
        max(signal_breakdown, key=lambda signal: signal_breakdown[signal])
        if signal_breakdown
        else None
    )

    return {
        "score": score,
        "label": label,
        "dominant_signal": dominant_signal,
        "signal_breakdown": signal_breakdown,
    }


def compute_fleet_risk(alerts_by_mmsi: dict[str, list[dict[str, Any]]]) -> dict[str, dict[str, Any]]:
    """
    Compute risk scores for all vessels in a fleet.

    Args:
        alerts_by_mmsi: Dict mapping MMSI → list of alert dicts

    Returns:
        Dict mapping MMSI → risk result dict
    """
    return {mmsi: compute_vessel_risk(alerts) for mmsi, alerts in alerts_by_mmsi.items()}
