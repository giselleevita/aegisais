"""Tests for multi-source data ingesters: EEZ, sanctions sync, weather, bathymetry, global cables."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ──────────────────────────────────────────────────────────────────────
# EEZ Boundary Service
# ──────────────────────────────────────────────────────────────────────

class TestEEZ:
    def test_identify_eez_in_uk_waters(self):
        from app.services.geodata.eez import identify_eez
        result = identify_eez(lon=-2.0, lat=55.0)
        assert result is not None
        assert result["iso3"] == "GBR"

    def test_identify_eez_in_norwegian_waters(self):
        from app.services.geodata.eez import identify_eez
        result = identify_eez(lon=5.0, lat=60.0)
        assert result is not None
        assert result["iso3"] == "NOR"

    def test_identify_eez_returns_valid_zone(self):
        from app.services.geodata.eez import identify_eez
        # Central Baltic — should match some NATO EEZ
        result = identify_eez(lon=20.0, lat=59.0)
        assert result is not None
        assert len(result["iso3"]) == 3
        assert result["sovereign"] != ""

    def test_international_waters(self):
        from app.services.geodata.eez import identify_eez
        # Mid-Atlantic, far from any coast
        result = identify_eez(lon=-30.0, lat=30.0)
        assert result is None

    def test_flag_eez_mismatch(self):
        from app.services.geodata.eez import check_flag_eez_mismatch
        result = check_flag_eez_mismatch(lon=-2.0, lat=55.0, vessel_flag_iso3="RUS")
        assert result is not None
        assert result["type"] == "FLAG_EEZ_MISMATCH"

    def test_flag_eez_match(self):
        from app.services.geodata.eez import check_flag_eez_mismatch
        result = check_flag_eez_mismatch(lon=-2.0, lat=55.0, vessel_flag_iso3="GBR")
        assert result is None

    def test_get_eez_zones_returns_bundled(self):
        from app.services.geodata.eez import get_eez_zones
        zones = get_eez_zones()
        assert len(zones) >= 15
        names = [z["name"] for z in zones]
        assert any("United Kingdom" in n for n in names)

    def test_point_in_polygon(self):
        from app.services.geodata.eez import _point_in_polygon
        # Simple square polygon
        square = [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]
        assert _point_in_polygon(5, 5, square) is True
        assert _point_in_polygon(15, 15, square) is False


# ──────────────────────────────────────────────────────────────────────
# Weather Service
# ──────────────────────────────────────────────────────────────────────

class TestWeather:
    def test_classify_sea_state(self):
        from app.services.weather import _classify_sea_state
        assert _classify_sea_state(0.05) == "calm_glassy"
        assert _classify_sea_state(0.3) == "calm_rippled"
        assert _classify_sea_state(1.0) == "smooth"
        assert _classify_sea_state(2.0) == "slight"
        assert _classify_sea_state(3.5) == "moderate"
        assert _classify_sea_state(5.0) == "rough"
        assert _classify_sea_state(7.0) == "very_rough"
        assert _classify_sea_state(10.0) == "high"
        assert _classify_sea_state(15.0) == "phenomenal"
        assert _classify_sea_state(None) == "unknown"

    def test_weather_relevant_for_anomaly_rough_seas(self):
        from app.services.weather import is_weather_relevant_for_anomaly
        weather = {"wave_height_m": 5.0, "sea_state": "rough"}
        result = is_weather_relevant_for_anomaly(weather, vessel_sog=8.0)
        assert result is not None
        assert result["weather_mitigating"] is True

    def test_weather_calm_slow_vessel(self):
        from app.services.weather import is_weather_relevant_for_anomaly
        weather = {"wave_height_m": 0.2, "sea_state": "calm_rippled"}
        result = is_weather_relevant_for_anomaly(weather, vessel_sog=1.0)
        assert result is not None
        assert result["weather_mitigating"] is False

    @pytest.mark.asyncio
    async def test_get_marine_weather_timeout(self):
        import httpx
        from app.services.weather import get_marine_weather

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))

        with patch("app.services.weather._get_client", return_value=mock_client):
            result = await get_marine_weather(57.5, 20.0)
            assert result is None

    @pytest.mark.asyncio
    async def test_get_marine_weather_success(self):
        from app.services.weather import get_marine_weather

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "current": {
                "time": "2026-04-01T12:00",
                "wave_height": 1.5,
                "wave_direction": 180,
                "wave_period": 6.0,
                "wind_wave_height": 1.0,
                "wind_wave_direction": 170,
                "swell_wave_height": 0.5,
                "swell_wave_direction": 200,
            }
        }
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)

        with patch("app.services.weather._get_client", return_value=mock_client):
            result = await get_marine_weather(57.5, 20.0)
            assert result is not None
            assert result["wave_height_m"] == 1.5
            assert result["sea_state"] == "slight"


# ──────────────────────────────────────────────────────────────────────
# Bathymetry Service
# ──────────────────────────────────────────────────────────────────────

class TestBathymetry:
    def test_classify_depth(self):
        from app.services.bathymetry import _classify_depth
        assert _classify_depth(10.0) == "land"
        assert _classify_depth(-5.0) == "very_shallow"
        assert _classify_depth(-30.0) == "shallow"
        assert _classify_depth(-100.0) == "coastal"
        assert _classify_depth(-500.0) == "continental_shelf"
        assert _classify_depth(-3000.0) == "deep_ocean"
        assert _classify_depth(-7000.0) == "hadal"

    def test_draft_depth_anomaly_on_land(self):
        from app.services.bathymetry import check_draft_depth_anomaly
        result = check_draft_depth_anomaly(depth_m=50.0)
        assert result is not None
        assert result["type"] == "POSITION_ON_LAND"
        assert result["severity"] == 90

    def test_draft_depth_anomaly_too_shallow(self):
        from app.services.bathymetry import check_draft_depth_anomaly
        result = check_draft_depth_anomaly(depth_m=-3.0, vessel_draft_m=10.0)
        assert result is not None
        assert result["type"] == "DRAFT_DEPTH_MISMATCH"
        assert result["severity"] == 85

    def test_draft_depth_ok(self):
        from app.services.bathymetry import check_draft_depth_anomaly
        result = check_draft_depth_anomaly(depth_m=-50.0, vessel_draft_m=10.0)
        assert result is None

    def test_vessel_type_depth_mismatch(self):
        from app.services.bathymetry import check_draft_depth_anomaly
        result = check_draft_depth_anomaly(depth_m=-5.0, vessel_type="container")
        assert result is not None
        assert result["type"] == "DEPTH_VESSEL_TYPE_MISMATCH"

    def test_depth_classification(self):
        from app.services.bathymetry import _classify_depth
        assert _classify_depth(10.0) == "land"
        assert _classify_depth(-5.0) == "very_shallow"
        assert _classify_depth(-100.0) == "coastal"
        assert _classify_depth(-3000.0) == "deep_ocean"

    @pytest.mark.asyncio
    async def test_get_depth_timeout(self):
        import httpx
        from app.services.bathymetry import get_depth_at_position

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))

        with patch("app.services.bathymetry._get_client", return_value=mock_client):
            result = await get_depth_at_position(57.5, 20.0)
            assert result is None


# ──────────────────────────────────────────────────────────────────────
# OFAC / EU Sanctions Loader
# ──────────────────────────────────────────────────────────────────────

class TestSanctionsLoader:
    @pytest.mark.asyncio
    async def test_fetch_ofac_handles_failure(self):
        from app.modules.sanctions.official_lists import fetch_ofac_sdn

        with patch("app.modules.sanctions.official_lists.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            instance.get = AsyncMock(side_effect=Exception("network error"))
            MockClient.return_value = instance

            result = await fetch_ofac_sdn()
            assert result == {"mmsi": [], "imo": [], "names": []}

    @pytest.mark.asyncio
    async def test_fetch_ofac_parses_vessel_rows(self):
        from app.modules.sanctions.official_lists import fetch_ofac_sdn

        # Simulate OFAC SDN CSV with a vessel entry
        csv_content = ','.join([
            '12345', 'TEST TANKER', 'vessel', 'SDGT', '', 'ABCD',
            'Crude Oil Tanker', '50000', '30000', 'Iran', 'Test Corp',
            'IMO 1234567; MMSI 412345678; some other data'
        ])

        mock_resp = MagicMock()
        mock_resp.text = csv_content
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()

        with patch("app.modules.sanctions.official_lists.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            instance.get = AsyncMock(return_value=mock_resp)
            MockClient.return_value = instance

            result = await fetch_ofac_sdn()
            assert "TEST TANKER" in result["names"]
            assert "1234567" in result["imo"]
            assert "412345678" in result["mmsi"]


# ──────────────────────────────────────────────────────────────────────
# Global Submarine Cable Network
# ──────────────────────────────────────────────────────────────────────

class TestGlobalCables:
    def test_global_cable_zones_loaded(self):
        from app.modules.itdae.geofences.global_cables import get_global_cable_zones
        zones = get_global_cable_zones()
        assert len(zones) >= 7
        ids = [z["id"] for z in zones]
        assert any("ns-" in i for i in ids)
        assert any("pac-" in i for i in ids)
        assert any("io-" in i for i in ids)
        assert any("af-" in i for i in ids)

    def test_infrastructure_db_includes_global(self):
        from app.modules.itdae.geofences.infrastructure_db import get_all_infrastructure_zones
        zones = get_all_infrastructure_zones()
        ids = [z["id"] for z in zones]
        # Should have Baltic + Mediterranean + Atlantic + Arctic + global
        assert any("baltic-" in i for i in ids)
        assert any("med-" in i for i in ids)
        assert any("atl-" in i for i in ids)
        assert any("arctic-" in i for i in ids)
        assert any("ns-" in i for i in ids)
        assert any("pac-" in i for i in ids)

    def test_all_zones_have_required_fields(self):
        from app.modules.itdae.geofences.infrastructure_db import get_all_infrastructure_zones
        for zone in get_all_infrastructure_zones():
            assert "id" in zone
            assert "name" in zone
            assert "polygon" in zone
            assert "risk_level" in zone
            assert zone["risk_level"] in ("critical", "high", "medium")


# ──────────────────────────────────────────────────────────────────────
# API Endpoint Integration
# ──────────────────────────────────────────────────────────────────────

class TestGeodataEndpoints:
    def test_eez_identify_endpoint(self):
        from fastapi.testclient import TestClient
        from app.main import app
        client = TestClient(app)
        resp = client.get("/v1/geodata/eez/identify", params={"lat": 55.0, "lon": -2.0})
        assert resp.status_code == 200
        data = resp.json()
        assert "eez" in data
        assert data["international_waters"] is False

    def test_eez_zones_endpoint(self):
        from fastapi.testclient import TestClient
        from app.main import app
        client = TestClient(app)
        resp = client.get("/v1/geodata/eez/zones")
        assert resp.status_code == 200
        assert resp.json()["count"] >= 15

    def test_flag_check_endpoint(self):
        from fastapi.testclient import TestClient
        from app.main import app
        client = TestClient(app)
        resp = client.get("/v1/geodata/eez/flag-check", params={
            "lat": 55.0, "lon": -2.0, "flag_iso3": "RUS",
        })
        assert resp.status_code == 200
        assert resp.json()["mismatch"] is True

    def test_sanctions_sync_endpoint_exists(self):
        from fastapi.testclient import TestClient
        from app.main import app
        client = TestClient(app)
        # We don't actually call the sync (hits external), just verify 405 on GET
        resp = client.get("/v1/sanctions/watchlist/sync")
        assert resp.status_code == 405  # Method not allowed (POST only)
