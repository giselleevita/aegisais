"""Tests for Featherless AI / LLM integration.

Covers:
- LLM client service (mocked httpx)
- Intel service with LLM enabled/disabled (graceful degradation)
- ML scoring enrichment
- Analyst chat endpoint
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ──────────────────────────────────────────────────────────────────────
# LLM Client
# ──────────────────────────────────────────────────────────────────────

class TestLLMClient:
    @pytest.mark.asyncio
    async def test_complete_returns_none_when_disabled(self):
        from app.services.llm import complete
        with patch("app.services.llm.is_llm_enabled", return_value=False):
            result = await complete("system", "user")
            assert result is None

    @pytest.mark.asyncio
    async def test_complete_returns_text_on_success(self):
        from app.services.llm import complete

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "LLM response text"}}]
        }
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)

        with (
            patch("app.services.llm.is_llm_enabled", return_value=True),
            patch("app.services.llm._get_client", return_value=mock_client),
        ):
            result = await complete("system", "user")
            assert result == "LLM response text"

    @pytest.mark.asyncio
    async def test_complete_returns_none_on_timeout(self):
        import httpx
        from app.services.llm import complete

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("timeout"))

        with (
            patch("app.services.llm.is_llm_enabled", return_value=True),
            patch("app.services.llm._get_client", return_value=mock_client),
        ):
            result = await complete("system", "user")
            assert result is None

    def test_is_llm_enabled_false_by_default(self):
        from app.services.llm import is_llm_enabled
        # Default config has LLM_ENABLED=False
        assert is_llm_enabled() is False


# ──────────────────────────────────────────────────────────────────────
# Intel Service — LLM integration
# ──────────────────────────────────────────────────────────────────────

class TestIntelWithLLM:
    @pytest.mark.asyncio
    async def test_intsum_uses_template_when_llm_disabled(self):
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
        assert "During the reporting period" in intsum["narrative"]
        assert intsum["threat_assessment"]["total_alerts"] == 2

    @pytest.mark.asyncio
    async def test_intsum_uses_llm_when_enabled(self):
        from app.modules.intel.service import generate_intsum

        async def mock_llm_intsum(*args, **kwargs):
            return "AI-generated intelligence summary with threat analysis."

        now = datetime.now(timezone.utc)
        with (
            patch("app.modules.intel.service.is_llm_enabled", return_value=True),
            patch("app.modules.intel.service.llm_intsum_narrative", side_effect=mock_llm_intsum),
        ):
            intsum = await generate_intsum(
                alerts=[{"type": "TELEPORT", "severity": 85, "mmsi": "211000001"}],
                period_start=now - timedelta(hours=24),
                period_end=now,
            )
            assert "AI-generated intelligence summary" in intsum["narrative"]

    @pytest.mark.asyncio
    async def test_intsum_falls_back_on_llm_failure(self):
        from app.modules.intel.service import generate_intsum

        async def mock_llm_fail(*args, **kwargs):
            return None

        now = datetime.now(timezone.utc)
        with (
            patch("app.modules.intel.service.is_llm_enabled", return_value=True),
            patch("app.modules.intel.service.llm_intsum_narrative", side_effect=mock_llm_fail),
        ):
            intsum = await generate_intsum(
                alerts=[{"type": "TELEPORT", "severity": 85, "mmsi": "211000001"}],
                period_start=now - timedelta(hours=24),
                period_end=now,
            )
            # Should fall back to template
            assert "During the reporting period" in intsum["narrative"]

    @pytest.mark.asyncio
    async def test_dossier_includes_analyst_assessment_when_llm_enabled(self):
        from app.modules.intel.service import generate_vessel_dossier

        async def mock_llm_dossier(*args, **kwargs):
            return "AI-generated risk assessment for vessel."

        with (
            patch("app.modules.intel.service.is_llm_enabled", return_value=True),
            patch("app.modules.intel.service.llm_dossier_assessment", side_effect=mock_llm_dossier),
        ):
            dossier = await generate_vessel_dossier(
                mmsi="211000001",
                alerts=[{"type": "TELEPORT", "severity": 80, "timestamp": "2025-01-01"}],
            )
            assert dossier["analyst_assessment"] == "AI-generated risk assessment for vessel."

    @pytest.mark.asyncio
    async def test_dossier_assessment_none_when_llm_disabled(self):
        from app.modules.intel.service import generate_vessel_dossier
        dossier = await generate_vessel_dossier(
            mmsi="211000001",
            alerts=[{"type": "TELEPORT", "severity": 80, "timestamp": "2025-01-01"}],
        )
        assert dossier["analyst_assessment"] is None

    @pytest.mark.asyncio
    async def test_area_sitrep_still_works(self):
        from app.modules.intel.service import generate_area_sitrep
        sitrep = await generate_area_sitrep(
            area_name="Baltic Sea",
            alerts=[],
            vessel_count=5,
        )
        assert sitrep["product_type"] == "AREA_SITREP"


# ──────────────────────────────────────────────────────────────────────
# ML Scoring — anomaly explanation enrichment
# ──────────────────────────────────────────────────────────────────────

class TestMLScoringEnrichment:
    @pytest.mark.asyncio
    async def test_enrich_adds_narrative_when_llm_enabled(self):
        from app.detection.ml_scoring import enrich_ensemble_with_narrative

        async def mock_explanation(*args, **kwargs):
            return "The vessel shows elevated anomaly patterns consistent with AIS spoofing."

        result = {
            "composite_score": 72,
            "rule_score": 80,
            "ml_score": 60,
            "contributions": [{"source": "rule", "type": "GPS_MANIPULATION", "severity": 80}],
        }
        with (
            patch("app.detection.ml_scoring.is_llm_enabled", return_value=True),
            patch("app.detection.ml_scoring.generate_anomaly_explanation", side_effect=mock_explanation),
        ):
            enriched = await enrich_ensemble_with_narrative(result, mmsi="211000001")
            assert "explanation_narrative" in enriched
            assert "AIS spoofing" in enriched["explanation_narrative"]

    @pytest.mark.asyncio
    async def test_enrich_noop_when_llm_disabled(self):
        from app.detection.ml_scoring import enrich_ensemble_with_narrative

        result = {"composite_score": 50, "rule_score": 60, "ml_score": 30, "contributions": []}
        enriched = await enrich_ensemble_with_narrative(result)
        assert "explanation_narrative" not in enriched


# ──────────────────────────────────────────────────────────────────────
# Analyst Chat endpoint
# ──────────────────────────────────────────────────────────────────────

class TestAnalystChat:
    @pytest.mark.asyncio
    async def test_chat_returns_503_when_disabled(self):
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)
        resp = client.post("/v1/analyst/chat", json={
            "messages": [{"role": "user", "content": "What is AIS spoofing?"}],
        })
        assert resp.status_code == 503

    @pytest.mark.asyncio
    async def test_chat_returns_response_when_enabled(self):
        from fastapi.testclient import TestClient
        from app.main import app

        async def mock_complete(system, user, **kwargs):
            return "AIS spoofing is the deliberate manipulation of AIS signals."

        client = TestClient(app)
        with (
            patch("app.modules.analyst.router.is_llm_enabled", return_value=True),
            patch("app.modules.analyst.router.complete", side_effect=mock_complete),
        ):
            resp = client.post("/v1/analyst/chat", json={
                "messages": [{"role": "user", "content": "What is AIS spoofing?"}],
            })
            assert resp.status_code == 200
            data = resp.json()
            assert "AIS spoofing" in data["content"]
            assert data["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_analyst_status_endpoint(self):
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)
        resp = client.get("/v1/analyst/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "enabled" in data
        assert "model" in data

    @pytest.mark.asyncio
    async def test_chat_rejects_empty_messages(self):
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)
        with patch("app.modules.analyst.router.is_llm_enabled", return_value=True):
            resp = client.post("/v1/analyst/chat", json={
                "messages": [{"role": "assistant", "content": "hi"}],
            })
            assert resp.status_code == 400
