"""Unit tests for ITDAE trajectory tracking features (Week 3)."""
import math
from datetime import datetime, timezone, timedelta
import pytest

from app.modules.itdae.tracking.features_itdae import (
    ItdaePoint,
    TrajectoryFeatures,
    implied_speed_knots_itdae,
    turn_rate_deg_per_sec,
    is_loitering,
    compute_trajectory_features,
    NM_TO_M,
)


def _pt(mmsi: str, lat: float, lon: float, sog: float = None, cog: float = None, dt_offset_sec: int = 0) -> ItdaePoint:
    ts = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc) + timedelta(seconds=dt_offset_sec)
    return ItdaePoint(mmsi=mmsi, timestamp=ts, lat=lat, lon=lon, speed=sog, course=cog)


class TestImpliedSpeed:
    def test_stationary(self):
        p1 = _pt("123456789", 55.0, 18.0, dt_offset_sec=0)
        p2 = _pt("123456789", 55.0, 18.0, dt_offset_sec=60)
        assert implied_speed_knots_itdae(p1, p2) == pytest.approx(0.0, abs=0.01)

    def test_zero_dt_returns_none(self):
        p1 = _pt("123456789", 55.0, 18.0, dt_offset_sec=0)
        assert implied_speed_knots_itdae(p1, p1) is None

    def test_known_speed(self):
        """1 nm in 1 hour = 1 knot. 1 nm lat ≈ 0.00899 degrees."""
        p1 = _pt("123456789", 55.0, 18.0, dt_offset_sec=0)
        p2 = _pt("123456789", 55.0 + (NM_TO_M / 111320), 18.0, dt_offset_sec=3600)
        speed = implied_speed_knots_itdae(p1, p2)
        assert speed is not None
        assert speed == pytest.approx(1.0, abs=0.05)


class TestTurnRate:
    def test_no_turn(self):
        p1 = _pt("123456789", 55.0, 18.0, cog=90.0, dt_offset_sec=0)
        p2 = _pt("123456789", 55.01, 18.01, cog=90.0, dt_offset_sec=60)
        assert turn_rate_deg_per_sec(p1, p2) == pytest.approx(0.0, abs=0.001)

    def test_90_degree_turn(self):
        p1 = _pt("123456789", 55.0, 18.0, cog=0.0, dt_offset_sec=0)
        p2 = _pt("123456789", 55.01, 18.01, cog=90.0, dt_offset_sec=90)
        rate = turn_rate_deg_per_sec(p1, p2)
        assert rate == pytest.approx(1.0, abs=0.01)

    def test_missing_cog_returns_none(self):
        p1 = _pt("123456789", 55.0, 18.0, dt_offset_sec=0)
        p2 = _pt("123456789", 55.01, 18.01, dt_offset_sec=60)
        assert turn_rate_deg_per_sec(p1, p2) is None


class TestLoitering:
    def test_loitering_detected(self):
        """Vessel sitting still for 35 minutes = loitering."""
        pts = [_pt("123456789", 55.0, 18.0, sog=0.5, dt_offset_sec=i * 300) for i in range(8)]
        assert is_loitering(pts) is True

    def test_no_loiter_too_fast(self):
        """Vessel moving at 8 kn = not loitering."""
        # 8 kn × 5min = ~0.67 nm per step → radius will exceed threshold
        step_deg = (8 * NM_TO_M / 111320) * (300 / 3600)
        pts = [_pt("123456789", 55.0 + i * step_deg, 18.0, sog=8.0, dt_offset_sec=i * 300) for i in range(8)]
        assert is_loitering(pts) is False

    def test_no_loiter_too_short(self):
        """Only 5 minutes of data = not enough duration."""
        pts = [_pt("123456789", 55.0, 18.0, sog=0.5, dt_offset_sec=i * 60) for i in range(3)]
        assert is_loitering(pts) is False

    def test_too_few_points(self):
        pts = [_pt("123456789", 55.0, 18.0)]
        assert is_loitering(pts) is False


class TestComputeFeatures:
    def test_returns_dataclass(self):
        p1 = _pt("123456789", 55.0, 18.0, sog=3.0, cog=90.0, dt_offset_sec=0)
        p2 = _pt("123456789", 55.0, 18.005, sog=3.0, cog=90.0, dt_offset_sec=120)
        feats = compute_trajectory_features(p1, p2, [p1, p2])
        assert isinstance(feats, TrajectoryFeatures)
        assert feats.mmsi == "123456789"
        assert feats.dt_sec == pytest.approx(120.0)
        assert feats.in_geofence is False  # Default
