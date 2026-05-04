"""Featherless AI / OpenAI-compatible LLM client for AegisAIS.

Provides async LLM inference for:
- Intelligence product narratives (INTSUM, dossiers, SITREPs)
- Anomaly explanation in natural language
- Maritime analyst assistant (conversational)

Uses httpx directly (already a dependency) against any OpenAI-compatible API.
Graceful degradation: if LLM is unavailable, falls back to template strings.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Optional

import httpx

_log = logging.getLogger("aegisais.llm")

# Module-level client — initialized lazily
_client: Optional[httpx.AsyncClient] = None
_client_loop: Optional[asyncio.AbstractEventLoop] = None


def _get_client() -> httpx.AsyncClient:
    global _client, _client_loop
    current_loop = asyncio.get_running_loop()

    # TestClient and ad-hoc scripts can execute requests on different event loops.
    # Recreate the async client when the loop changes so httpx does not try to reuse
    # transports bound to a closed loop.
    if _client is None or _client.is_closed or _client_loop is not current_loop:
        from app.core.config import settings
        _client = httpx.AsyncClient(
            base_url=settings.LLM_BASE_URL.rstrip("/"),
            headers={
                "Authorization": f"Bearer {settings.LLM_API_KEY}",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(settings.LLM_TIMEOUT_SEC, connect=10.0),
        )
        _client_loop = current_loop
    return _client


def is_llm_enabled() -> bool:
    """Check if LLM integration is configured and available."""
    from app.core.config import settings
    return bool(settings.LLM_ENABLED and settings.LLM_API_KEY)


async def get_llm_provider_status() -> dict[str, Any]:
    """Probe the configured LLM provider without exposing credentials.

    Uses the OpenAI-compatible ``GET /models`` route to distinguish between:
    - disabled / not configured
    - network or timeout failures
    - authentication failures
    - successful authenticated connectivity
    """
    from app.core.config import settings

    configured = bool(settings.LLM_ENABLED and settings.LLM_API_KEY and settings.LLM_BASE_URL)
    if not configured:
        return {
            "configured": False,
            "reachable": False,
            "authenticated": False,
            "status": "disabled",
            "http_status": None,
            "error": "LLM integration not configured",
        }

    try:
        client = _get_client()
        resp = await client.get("/models")

        if resp.status_code in {401, 403}:
            return {
                "configured": True,
                "reachable": True,
                "authenticated": False,
                "status": "auth_failed",
                "http_status": resp.status_code,
                "error": "Provider rejected credentials",
            }

        resp.raise_for_status()
        return {
            "configured": True,
            "reachable": True,
            "authenticated": True,
            "status": "ok",
            "http_status": resp.status_code,
            "error": None,
        }
    except httpx.TimeoutException:
        return {
            "configured": True,
            "reachable": False,
            "authenticated": False,
            "status": "timeout",
            "http_status": None,
            "error": "Provider request timed out",
        }
    except httpx.RequestError as e:
        return {
            "configured": True,
            "reachable": False,
            "authenticated": False,
            "status": "network_error",
            "http_status": None,
            "error": str(e),
        }
    except httpx.HTTPStatusError as e:
        return {
            "configured": True,
            "reachable": True,
            "authenticated": False,
            "status": "http_error",
            "http_status": e.response.status_code,
            "error": f"Provider returned HTTP {e.response.status_code}",
        }
    except Exception as e:
        _log.warning("LLM provider probe failed: %s", e)
        return {
            "configured": True,
            "reachable": False,
            "authenticated": False,
            "status": "error",
            "http_status": None,
            "error": str(e),
        }


async def complete(
    system_prompt: str,
    user_prompt: str,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> Optional[str]:
    """Send a chat completion request to the LLM API.

    Returns the generated text, or None if the call fails.
    Never raises — all errors are logged and return None for graceful degradation.
    """
    if not is_llm_enabled():
        return None

    from app.core.config import settings

    payload = {
        "model": settings.LLM_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature or settings.LLM_TEMPERATURE,
        "max_tokens": max_tokens or settings.LLM_MAX_TOKENS,
    }

    try:
        client = _get_client()
        resp = await client.post("/chat/completions", json=payload)
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        _log.debug("LLM response received (%d chars)", len(content))
        return content.strip()
    except httpx.TimeoutException:
        _log.warning("LLM request timed out — falling back to template")
        return None
    except httpx.HTTPStatusError as e:
        _log.warning("LLM API error %d: %s", e.response.status_code, e.response.text[:200])
        return None
    except Exception as e:
        _log.warning("LLM call failed: %s", e)
        return None


async def complete_streaming(
    system_prompt: str,
    user_prompt: str,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
):
    """Stream a chat completion response, yielding text chunks.

    Yields str chunks as they arrive. For SSE-based streaming endpoints.
    """
    if not is_llm_enabled():
        return

    from app.core.config import settings

    payload = {
        "model": settings.LLM_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature or settings.LLM_TEMPERATURE,
        "max_tokens": max_tokens or settings.LLM_MAX_TOKENS,
        "stream": True,
    }

    try:
        client = _get_client()
        async with client.stream("POST", "/chat/completions", json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                chunk_data = line[6:]
                if chunk_data.strip() == "[DONE]":
                    break
                try:
                    chunk = json.loads(chunk_data)
                    delta = chunk["choices"][0].get("delta", {})
                    content = delta.get("content")
                    if content:
                        yield content
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue
    except Exception as e:
        _log.warning("LLM streaming failed: %s", e)


# ──────────────────────────────────────────────────────────────────────
# Domain-specific system prompts
# ──────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT_INTSUM = """You are a NATO maritime intelligence analyst writing an Intelligence Summary (INTSUM).

Write in formal military intelligence style:
- Use past tense for observed events
- Be specific about vessel identifiers (MMSI), locations, and timestamps
- Assess threat level with evidence-based reasoning
- Recommend analyst actions where appropriate
- Keep the narrative to 2-3 concise paragraphs
- Do NOT speculate beyond the data provided
- Reference alert types using their technical names (TELEPORT, AIS_DARK, GPS_MANIPULATION, STS_TRANSFER, SANCTIONS_MATCH, etc.)

Classification: NATO RESTRICTED — handle accordingly."""

SYSTEM_PROMPT_DOSSIER = """You are a NATO maritime intelligence analyst writing a vessel risk assessment for a dossier/briefing aid.

Write in formal intelligence assessment style:
- Summarize the vessel's behavioral profile based on alerts, sanctions matches, and dark events
- Assess the risk level with evidence-based reasoning
- Identify the most likely threat hypothesis (sanctions evasion, spoofing, CIP threat, etc.)
- Recommend specific follow-up actions (continued monitoring, boarding, allied notification, etc.)
- Keep to 1-2 concise paragraphs
- Do NOT speculate beyond the data provided"""

SYSTEM_PROMPT_ANOMALY = """You are a maritime anomaly detection system explaining alert findings to a naval analyst.

Write in clear, concise technical prose:
- Explain what the composite anomaly score means in operational terms
- Describe which factors contributed most and why they matter
- Suggest what the pattern might indicate (without definitive attribution)
- Keep to 2-4 sentences"""

SYSTEM_PROMPT_ANALYST = """You are AegisAIS Maritime Analyst — an AI assistant for NATO maritime domain awareness analysts.

Your capabilities:
- Interpret AIS anomaly alerts (teleport, spoofing, dark vessel, sanctions match, STS transfer)
- Explain detection patterns and what they might indicate
- Provide context on maritime security threats (sanctions evasion, CIP threats, naval activity)
- Help analysts prioritize and triage alerts
- Suggest follow-up actions

Rules:
- Always ground your analysis in the data provided
- Clearly distinguish between confirmed facts and assessed judgments
- Use NATO/maritime terminology appropriately
- Never fabricate vessel identifiers, positions, or timestamps
- If you don't have enough data to answer, say so
- Keep responses concise and actionable"""


# ──────────────────────────────────────────────────────────────────────
# High-level domain functions
# ──────────────────────────────────────────────────────────────────────

async def generate_intsum_narrative(
    total_alerts: int,
    critical_count: int,
    high_count: int,
    threat_level: str,
    area: str,
    type_counts: dict[str, int],
    top_vessels: list[dict[str, Any]],
    period_start: str,
    period_end: str,
) -> Optional[str]:
    """Generate an LLM-powered INTSUM narrative."""
    user_prompt = f"""Generate an INTSUM narrative for the following data:

Area: {area}
Period: {period_start} to {period_end}
Total alerts: {total_alerts}
Critical alerts: {critical_count}
High alerts: {high_count}
Assessed threat level: {threat_level}

Alert type breakdown:
{json.dumps(type_counts, indent=2)}

Top vessels of interest (MMSI: alert count):
{json.dumps(top_vessels, indent=2)}

Write a 2-3 paragraph intelligence summary."""

    return await complete(SYSTEM_PROMPT_INTSUM, user_prompt, temperature=0.3, max_tokens=600)


async def generate_dossier_assessment(
    mmsi: str,
    risk_level: str,
    alert_count: int,
    max_severity: int,
    sanctions_flagged: bool,
    dark_event_count: int,
    alert_types: list[str],
    ml_score: Optional[dict[str, Any]] = None,
) -> Optional[str]:
    """Generate an LLM-powered vessel risk assessment for a dossier."""
    user_prompt = f"""Generate a risk assessment for the following vessel:

MMSI: {mmsi}
Risk level: {risk_level}
Total alerts: {alert_count}
Max alert severity: {max_severity}
Sanctions flagged: {sanctions_flagged}
AIS dark events: {dark_event_count}
Alert types observed: {', '.join(alert_types)}
ML anomaly score: {json.dumps(ml_score) if ml_score else 'N/A'}

Write a 1-2 paragraph analyst assessment with recommended follow-up actions."""

    return await complete(SYSTEM_PROMPT_DOSSIER, user_prompt, temperature=0.3, max_tokens=400)


async def generate_anomaly_explanation(
    composite_score: int,
    rule_score: int,
    ml_score: float,
    contributions: list[dict[str, Any]],
    mmsi: Optional[str] = None,
) -> Optional[str]:
    """Generate an LLM-powered explanation of anomaly scoring."""
    user_prompt = f"""Explain this anomaly assessment to a maritime analyst:

Vessel MMSI: {mmsi or 'unknown'}
Composite score: {composite_score}/100
Rule-based score: {rule_score}/100
ML statistical score: {ml_score:.1f}/100

Contributing factors:
{json.dumps(contributions, indent=2)}

Write 2-4 sentences explaining what this means operationally."""

    return await complete(SYSTEM_PROMPT_ANOMALY, user_prompt, temperature=0.3, max_tokens=200)
