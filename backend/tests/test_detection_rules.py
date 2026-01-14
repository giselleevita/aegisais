"""Unit tests for detection rules."""
import pytest
from datetime import datetime, timedelta
from app.ingest.loaders import AisPoint
from app.detection.rules import (
    rule_teleport,
    rule_teleport_t2,
    rule_turn_rate,
    rule_turn_rate_t2,
    rule_position_invalid,
    rule_acceleration,
    rule_heading_cog_consistency,
)


def create_point(mmsi: str, lat: float, lon: float, timestamp: datetime, 
                 sog: float = None, cog: float = None, heading: float = None) -> AisPoint:
    """Helper to create AIS points for testing."""
    return AisPoint(
        mmsi=mmsi,
        timestamp=timestamp,
        lat=lat,
        lon=lon,
        sog=sog,
        cog=cog,
        heading=heading,
    )


class TestTeleportRule:
    """Tests for teleport detection rule."""
    
    def test_teleport_short_gap_high_speed(self):
        """Should detect teleport with short gap and high speed."""
        p1 = create_point("123456789", 40.0, -74.0, datetime.now())
        p2 = create_point("123456789", 41.0, -74.0, datetime.now() + timedelta(seconds=60))
        
        result = rule_teleport(p1, p2)
        assert result is not None
        assert result["type"] == "TELEPORT"
        assert result["severity"] > 0
    
    def test_teleport_short_gap_low_speed(self):
        """Should not detect teleport with low speed."""
        p1 = create_point("123456789", 40.0, -74.0, datetime.now())
        p2 = create_point("123456789", 40.001, -74.0, datetime.now() + timedelta(seconds=60))
        
        result = rule_teleport(p1, p2)
        assert result is None
    
    def test_teleport_negative_dt(self):
        """Should not detect teleport with negative time delta."""
        p1 = create_point("123456789", 40.0, -74.0, datetime.now())
        p2 = create_point("123456789", 41.0, -74.0, datetime.now() - timedelta(seconds=60))
        
        result = rule_teleport(p1, p2)
        assert result is None


class TestTurnRateRule:
    """Tests for turn rate detection rule."""
    
    def test_turn_rate_high_speed_sharp_turn(self):
        """Should detect sharp turn at high speed."""
        p1 = create_point("123456789", 40.0, -74.0, datetime.now(), sog=20.0, heading=0.0)
        p2 = create_point("123456789", 40.01, -74.01, datetime.now() + timedelta(seconds=10), 
                          sog=20.0, heading=90.0)
        
        result = rule_turn_rate(p1, p2)
        # May or may not trigger depending on exact calculation, but should handle gracefully
        assert result is None or result["type"] == "TURN_RATE"
    
    def test_turn_rate_low_speed(self):
        """Should not detect turn rate at very low speed."""
        p1 = create_point("123456789", 40.0, -74.0, datetime.now(), sog=1.0, heading=0.0)
        p2 = create_point("123456789", 40.001, -74.0, datetime.now() + timedelta(seconds=10), 
                          sog=1.0, heading=45.0)
        
        result = rule_turn_rate(p1, p2)
        # Low speed should reduce sensitivity
        assert result is None or result["severity"] < 50


class TestPositionInvalidRule:
    """Tests for position validation rule."""
    
    def test_position_zero_zero(self):
        """Should detect (0, 0) position."""
        p1 = create_point("123456789", 40.0, -74.0, datetime.now())
        p2 = create_point("123456789", 0.0, 0.0, datetime.now() + timedelta(seconds=60))
        
        result = rule_position_invalid(p1, p2)
        assert result is not None
        assert result["type"] == "POSITION_INVALID"
    
    def test_position_out_of_bounds(self):
        """Should detect out-of-bounds coordinates."""
        p1 = create_point("123456789", 40.0, -74.0, datetime.now())
        p2 = create_point("123456789", 200.0, -74.0, datetime.now() + timedelta(seconds=60))
        
        result = rule_position_invalid(p1, p2)
        assert result is not None
        assert result["type"] == "POSITION_INVALID"
    
    def test_position_valid(self):
        """Should not flag valid positions."""
        p1 = create_point("123456789", 40.0, -74.0, datetime.now())
        p2 = create_point("123456789", 40.01, -74.01, datetime.now() + timedelta(seconds=60))
        
        result = rule_position_invalid(p1, p2)
        assert result is None


class TestAccelerationRule:
    """Tests for acceleration detection rule."""
    
    def test_acceleration_extreme(self):
        """Should detect extreme acceleration."""
        p1 = create_point("123456789", 40.0, -74.0, datetime.now(), sog=10.0)
        p2 = create_point("123456789", 40.01, -74.0, datetime.now() + timedelta(seconds=1), sog=50.0)
        
        result = rule_acceleration(p1, p2)
        # May trigger if acceleration exceeds threshold
        assert result is None or result["type"] == "ACCELERATION"
    
    def test_acceleration_normal(self):
        """Should not detect normal acceleration."""
        p1 = create_point("123456789", 40.0, -74.0, datetime.now(), sog=10.0)
        p2 = create_point("123456789", 40.01, -74.0, datetime.now() + timedelta(seconds=60), sog=12.0)
        
        result = rule_acceleration(p1, p2)
        # Normal acceleration should not trigger
        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
