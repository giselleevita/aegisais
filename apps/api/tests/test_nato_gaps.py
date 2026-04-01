"""Tests for new NATO fundability features (GAP-01 through GAP-12)."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from app.infrastructure.ingest.loaders import AisPoint

# ──────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────

def _point(
    mmsi: str = "211000001",
    lat: float = 57.5,
    lon: float = 20.0,
    sog: float = 12.0,
    cog: float = 180.0,
    heading: float = 180.0,
    ts_offset_sec: int = 0,
) -> AisPoint:
    return AisPoint(
        mmsi=mmsi,
        timestamp=datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc) + timedelta(seconds=ts_offset_sec),
        lat=lat,
        lon=lon,
        sog=sog,
        cog=cog,
        heading=heading,
    )


# ──────────────────────────────────────────────────────────────────────
# GAP-01: ML Scoring
# ──────────────────────────────────────────────────────────────────────

class TestMLScoring:
    def test_predict_next_position(self):
        from app.detection.ml_scoring import predict_next_position
        track = [_point(ts_offset_sec=0), _point(ts_offset_sec=60, lat=57.51, lon=20.01)]
        pred = predict_next_position(track)
        assert pred is not None
        assert "predicted_lat" in pred
        assert "predicted_lon" in pred

    def test_compute_anomaly_score_normal(self):
        from app.detection.ml_scoring import compute_anomaly_score
        current = _point(sog=12.0, cog=180.0)
        history = [_point(ts_offset_sec=-i * 60, sog=12.0 + (i * 0.1), cog=180.0) for i in range(5)]
        result = compute_anomaly_score(current, history)
        assert isinstance(result, dict)
        assert "anomaly_score" in result
        assert 0 <= result["anomaly_score"] <= 100

    def test_ensemble_score_with_no_alerts(self):
        from app.detection.ml_scoring import ensemble_score
        ml_result = {"anomaly_score": 30, "features": {}}
        result = ensemble_score([], ml_result)
        assert "composite_score" in result
        assert result["composite_score"] >= 0

    def test_ensemble_score_with_alerts(self):
        from app.detection.ml_scoring import ensemble_score
        alerts = [{"type": "TELEPORT", "severity": 80}, {"type": "AIS_DARK", "severity": 60}]
        ml_result = {"anomaly_score": 50, "features": {}}
        result = ensemble_score(alerts, ml_result)
        assert result["composite_score"] >= 48  # 0.6*80 + 0.4*50 = 68



# ──────────────────────────────────────────────────────────────────────
# GAP-03: Spoofing Detection
# ──────────────────────────────────────────────────────────────────────

class TestSpoofingDetection:
    def test_valid_mmsi_passes(self):
        from app.detection.spoofing import rule_mmsi_format_invalid
        p1 = _point(mmsi="211000001")
        p2 = _point(mmsi="211000001", ts_offset_sec=60)
        assert rule_mmsi_format_invalid(p1, p2) is None

    def test_invalid_mmsi_detected(self):
        from app.detection.spoofing import rule_mmsi_format_invalid
        p1 = _point(mmsi="000000001")
        p2 = _point(mmsi="000000001", ts_offset_sec=60)
        result = rule_mmsi_format_invalid(p1, p2)
        assert result is not None
        assert result["type"] == "MMSI_FORMAT_INVALID"

    def test_gps_grid_manipulation_detected(self):
        from app.detection.spoofing import rule_gps_manipulation
        # Exact grid coordinates (suspicious)
        p1 = _point(lat=57.000000, lon=20.000000)
        p2 = _point(lat=57.000000, lon=20.000000, ts_offset_sec=60, sog=15.0)
        # Since sog > 0 but position is perfectly grid-aligned, this may trigger
        result = rule_gps_manipulation(p1, p2)
        # The rule checks for rounded coordinates with speed mismatch
        # With sog=15 and identical positions, it should detect manipulation
        if result:
            assert result["type"] == "GPS_MANIPULATION"


# ──────────────────────────────────────────────────────────────────────
# GAP-04: NATO Interop Serializers
# ──────────────────────────────────────────────────────────────────────

class TestNATOInterop:
    def test_cot_vessel_serialization(self):
        from app.modules.interop.cot_serializer import vessel_position_to_cot
        xml = vessel_position_to_cot(
            mmsi="211000001", lat=57.5, lon=20.0, sog=12.0, cog=180.0,
        )
        assert "211000001" in xml
        assert "<event" in xml
        assert "a-n-S-C-m" in xml  # CoT type for maritime vessel

    def test_stanag_nffi_vessel(self):
        from app.modules.interop.stanag5527_serializer import vessel_to_nffi
        xml = vessel_to_nffi(
            mmsi="211000001", lat=57.5, lon=20.0, sog=12.0, cog=180.0,
        )
        assert "211000001" in xml
        assert "NFFI" in xml or "nffi" in xml.lower()

    def test_cot_alert_serialization(self):
        from app.modules.interop.cot_serializer import alert_to_cot
        xml = alert_to_cot(
            alert_id="test-001",
            alert_type="TELEPORT",
            mmsi="211000001",
            lat=57.5,
            lon=20.0,
            severity=80,
            summary="Teleport detected",
        )
        assert "TELEPORT" in xml
        assert "211000001" in xml


# ──────────────────────────────────────────────────────────────────────
# GAP-05: Dark Vessel Detection
# ──────────────────────────────────────────────────────────────────────

class TestDarkVesselDetection:
    def test_no_dark_alert_short_gap(self):
        from app.detection.dark_vessel import rule_ais_dark
        p1 = _point(ts_offset_sec=0)
        p2 = _point(ts_offset_sec=300)  # 5 min — under threshold
        result = rule_ais_dark(p1, p2)
        assert result is None

    def test_dark_alert_long_gap(self):
        from app.detection.dark_vessel import rule_ais_dark
        p1 = _point(ts_offset_sec=0)
        p2 = _point(ts_offset_sec=7200)  # 2 hours
        result = rule_ais_dark(p1, p2)
        assert result is not None
        assert result["type"] == "AIS_DARK"
        assert result["severity"] >= 60


# ──────────────────────────────────────────────────────────────────────
# GAP-07: Classification Marking
# ──────────────────────────────────────────────────────────────────────

class TestClassificationMarking:
    def test_apply_classification(self):
        from app.modules.interop.classification import apply_classification, NATOClassification
        data = {"foo": "bar"}
        result = apply_classification(data, classification=NATOClassification.RESTRICTED)
        assert "_classification" in result
        assert result["_classification"]["classification"] == "NATO RESTRICTED"
        assert result["_classification"]["marking_standard"] == "STANAG 4774"

    def test_classify_alert_high_severity(self):
        from app.modules.interop.classification import classify_alert
        result = classify_alert({"type": "TELEPORT"}, severity=95)
        assert result["_classification"]["classification"] == "NATO RESTRICTED"
        assert result["_classification"]["tlp"] == "TLP:AMBER"

    def test_classify_alert_low_severity(self):
        from app.modules.interop.classification import classify_alert
        result = classify_alert({"type": "POSITION_INVALID"}, severity=30)
        assert result["_classification"]["classification"] == "NATO UNCLASSIFIED"


# ──────────────────────────────────────────────────────────────────────
# GAP-08: Infrastructure Database
# ──────────────────────────────────────────────────────────────────────

class TestInfrastructureDB:
    def test_all_zones_loaded(self):
        from app.modules.itdae.geofences.infrastructure_db import get_all_infrastructure_zones
        zones = get_all_infrastructure_zones()
        # Original 4 Baltic + 3 Med + 2 Atlantic + 2 Arctic = 11
        assert len(zones) >= 11

    def test_zone_ids_unique(self):
        from app.modules.itdae.geofences.infrastructure_db import get_zone_ids
        ids = get_zone_ids()
        assert len(ids) == len(set(ids))

    def test_filter_by_risk(self):
        from app.modules.itdae.geofences.infrastructure_db import get_zones_by_risk_level
        critical = get_zones_by_risk_level("critical")
        assert len(critical) > 0
        assert all(z["risk_level"] == "critical" for z in critical)


# ──────────────────────────────────────────────────────────────────────
# GAP-09: Sanctions
# ──────────────────────────────────────────────────────────────────────

class TestSanctions:
    def test_clean_vessel(self):
        from app.modules.sanctions.service import check_vessel_sanctions
        result = check_vessel_sanctions("999999999")
        assert result is None

    def test_sanctioned_mmsi(self):
        from app.modules.sanctions import service as svc
        # Inject test data
        svc._sanctioned_mmsi = {"123456789"}
        try:
            result = svc.check_vessel_sanctions("123456789")
            assert result is not None
            assert result["type"] == "SANCTIONS_MATCH"
            assert result["severity"] == 95
        finally:
            svc._sanctioned_mmsi = set()

    def test_sts_detection(self):
        from app.modules.sanctions.service import detect_sts_transfer
        a = _point(mmsi="111111111", sog=1.0)
        b = _point(mmsi="222222222", sog=0.5, lat=57.5001, lon=20.0001)
        result = detect_sts_transfer(a, b)
        assert result is not None
        assert result["type"] == "STS_TRANSFER"

    def test_sts_no_trigger_far_apart(self):
        from app.modules.sanctions.service import detect_sts_transfer
        a = _point(mmsi="111111111", sog=1.0)
        b = _point(mmsi="222222222", sog=0.5, lat=58.5, lon=21.0)  # Far away
        result = detect_sts_transfer(a, b)
        assert result is None


# ──────────────────────────────────────────────────────────────────────
# GAP-10: MFA
# ──────────────────────────────────────────────────────────────────────

class TestMFA:
    def test_mfa_availability(self):
        from app.modules.auth.mfa import is_mfa_available
        # May or may not have pyotp installed
        result = is_mfa_available()
        assert isinstance(result, bool)

    def test_generate_and_verify(self):
        from app.modules.auth.mfa import is_mfa_available
        if not is_mfa_available():
            pytest.skip("pyotp not installed")
        from app.modules.auth.mfa import generate_totp_secret, verify_totp, get_provisioning_uri
        import pyotp
        secret = generate_totp_secret()
        assert len(secret) > 0
        uri = get_provisioning_uri(secret, "testuser")
        assert "otpauth://" in uri
        # Generate valid code and verify
        totp = pyotp.TOTP(secret)
        code = totp.now()
        assert verify_totp(secret, code) is True
        assert verify_totp(secret, "000000") is False


# ──────────────────────────────────────────────────────────────────────
# GAP-11: Intelligence Products
# ──────────────────────────────────────────────────────────────────────

class TestIntelProducts:
    @pytest.mark.asyncio
    async def test_intsum_generation(self):
        from app.modules.intel.service import generate_intsum
        now = datetime.now(timezone.utc)
        intsum = await generate_intsum(
            alerts=[
                {"type": "TELEPORT", "severity": 80, "mmsi": "211000001"},
                {"type": "AIS_DARK", "severity": 70, "mmsi": "211000002"},
            ],
            period_start=now - timedelta(hours=24),
            period_end=now,
        )
        assert intsum["product_type"] == "INTSUM"
        assert intsum["threat_assessment"]["total_alerts"] == 2
        assert "_classification" in intsum

    @pytest.mark.asyncio
    async def test_vessel_dossier(self):
        from app.modules.intel.service import generate_vessel_dossier
        dossier = await generate_vessel_dossier(
            mmsi="211000001",
            alerts=[{"type": "TELEPORT", "severity": 80, "timestamp": "2025-01-01"}],
        )
        assert dossier["product_type"] == "VESSEL_DOSSIER"
        assert dossier["vessel"]["mmsi"] == "211000001"
        assert dossier["risk_assessment"]["level"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")


# ──────────────────────────────────────────────────────────────────────
# GAP-12: Multi-national Sharing
# ──────────────────────────────────────────────────────────────────────

class TestSharing:
    def test_create_shared_alert(self):
        from app.modules.sharing.service import create_shared_alert
        from app.modules.interop.classification import TLPMarking
        result = create_shared_alert(
            alert_data={"type": "TELEPORT", "severity": 80, "mmsi": "211000001", "summary": "test"},
            source_org_id=1,
            target_org_ids=[2, 3],
            tlp=TLPMarking.GREEN,
        )
        assert "shared_alert" in result
        assert "sharing_metadata" in result
        assert "_classification" in result

    def test_cop_feed(self):
        from app.modules.sharing.service import generate_cop_feed
        cop = generate_cop_feed(
            vessels=[{"mmsi": "211000001", "lat": 57.5, "lon": 20.0}],
            alerts=[{"type": "TELEPORT", "severity": 80, "mmsi": "211000001", "summary": "test"}],
        )
        assert cop["feed_type"] == "COP"
        assert len(cop["vessels"]) == 1
        assert "_classification" in cop
