from app.services.pilot_metrics import (
    build_pilot_kpi_summary,
    calculate_analyst_time_saved_seconds,
    calculate_detection_lead_time_seconds,
    calculate_false_alert_rate,
)


def test_calculate_detection_lead_time_seconds_uses_median():
    records = [
        {"ingested_at": 10.0, "alert_created_at": 25.0},
        {"ingested_at": 12.0, "alert_created_at": 27.0},
        {"ingested_at": 15.0, "alert_created_at": 45.0},
    ]
    assert calculate_detection_lead_time_seconds(records) == 15.0


def test_calculate_false_alert_rate_uses_reviewed_alerts_only():
    records = [
        {"reviewed": True, "is_false_alert": True},
        {"reviewed": True, "is_false_alert": False},
        {"reviewed": False, "is_false_alert": True},
    ]
    assert calculate_false_alert_rate(records) == 0.5


def test_calculate_analyst_time_saved_seconds_uses_median_delta():
    records = [
        {"baseline_seconds": 300.0, "pilot_seconds": 180.0},
        {"baseline_seconds": 200.0, "pilot_seconds": 150.0},
        {"baseline_seconds": 240.0, "pilot_seconds": 120.0},
    ]
    assert calculate_analyst_time_saved_seconds(records) == 120.0


def test_build_pilot_kpi_summary_combines_metrics():
    summary = build_pilot_kpi_summary(
        detection_records=[{"ingested_at": 0.0, "alert_created_at": 10.0}],
        review_records=[{"reviewed": True, "is_false_alert": False}],
        workflow_records=[{"baseline_seconds": 100.0, "pilot_seconds": 80.0}],
    )
    assert summary.to_dict() == {
        "detection_lead_time_seconds": 10.0,
        "false_alert_rate": 0.0,
        "analyst_time_saved_seconds": 20.0,
    }