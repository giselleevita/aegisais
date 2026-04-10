#!/usr/bin/env python3
"""Live smoke test for the configured LLM integration.

Checks three layers:
1. Direct provider chat-completions request
2. In-app provider status endpoint
3. End-to-end analyst chat endpoint

This script reads the local environment and intentionally never prints secrets.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

import httpx
from fastapi.testclient import TestClient

from app.main import app


def _require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Required environment variable missing: {name}")
    return value


def _print_header(title: str) -> None:
    print(f"\n== {title} ==")


def _direct_provider_check() -> dict[str, Any]:
    base_url = _require_env("LLM_BASE_URL").rstrip("/")
    api_key = _require_env("LLM_API_KEY")
    model = os.environ.get("LLM_MODEL", "Qwen/Qwen3-32B")

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Answer in one short sentence."},
            {"role": "user", "content": "Reply with exactly: featherless smoke ok"},
        ],
        "temperature": 0,
        "max_tokens": 16,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    with httpx.Client(timeout=30.0) as client:
        response = client.post(f"{base_url}/chat/completions", headers=headers, json=payload)

    result: dict[str, Any] = {
        "status_code": response.status_code,
        "ok": response.status_code == 200,
    }
    if response.status_code == 200:
        data = response.json()
        result["model"] = data.get("model")
        result["content"] = data["choices"][0]["message"].get("content", "").strip()
    else:
        result["error"] = response.text[:300]
    return result


def _api_status_check() -> dict[str, Any]:
    client = TestClient(app)
    response = client.get("/v1/analyst/status")
    return {
        "status_code": response.status_code,
        "body": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text,
    }


def _api_chat_check() -> dict[str, Any]:
    client = TestClient(app)
    response = client.post(
        "/v1/analyst/chat",
        json={
            "messages": [
                {"role": "user", "content": "In one short sentence, what does AIS spoofing mean?"}
            ],
            "stream": False,
        },
    )
    return {
        "status_code": response.status_code,
        "body": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text,
    }


def main() -> int:
    try:
        _require_env("LLM_ENABLED")
        _require_env("LLM_BASE_URL")
        _require_env("LLM_API_KEY")
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    _print_header("Direct Provider Check")
    provider = _direct_provider_check()
    print(json.dumps(provider, indent=2))

    _print_header("API Analyst Status")
    api_status = _api_status_check()
    print(json.dumps(api_status, indent=2))

    _print_header("API Analyst Chat")
    api_chat = _api_chat_check()
    print(json.dumps(api_chat, indent=2))

    provider_ok = provider.get("ok") is True
    status_ok = api_status.get("status_code") == 200 and api_status["body"].get("provider_status", {}).get("authenticated") is True
    chat_ok = api_chat.get("status_code") == 200 and bool(api_chat["body"].get("content"))

    if provider_ok and status_ok and chat_ok:
        print("\nLLM smoke test: OK")
        return 0

    print("\nLLM smoke test: FAILED", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())