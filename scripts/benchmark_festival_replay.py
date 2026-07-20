#!/usr/bin/env python3
"""Run repeated real-stack festival replays and enforce latency/state gates."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


API_URL = os.environ.get("API_URL", "http://127.0.0.1:8000").rstrip("/")
USERNAME = os.environ.get("FESTIVAL_TEST_USERNAME", "")
PASSWORD = os.environ.get("FESTIVAL_TEST_PASSWORD", "")
RUNS = int(os.environ.get("FESTIVAL_BENCHMARK_RUNS", "5"))
MAX_LATENCY_SEC = float(os.environ.get("FESTIVAL_MAX_LATENCY_SEC", "5"))
OUTPUT = Path(os.environ.get("FESTIVAL_LATENCY_OUTPUT", "festival-latency.json"))
EXPECTED = {
    "persistedObservations": 5,
    "festivalPositions": 4,
    "festivalVessels": 2,
    "fusionEvents": 2,
    "fusionAlerts": 2,
}


def _request(path: str, *, method: str = "GET", token: str | None = None, body: bytes | None = None) -> Any:
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if body is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    request = Request(f"{API_URL}{path}", data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=10) as response:
            return json.load(response)
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {path} failed with {exc.code}: {detail}") from exc


def _login() -> str:
    if not USERNAME or not PASSWORD:
        raise RuntimeError("Festival acceptance credentials are required")
    payload = urlencode({"username": USERNAME, "password": PASSWORD}).encode()
    return str(_request("/v1/auth/login", method="POST", body=payload)["access_token"])


def _wait_for_expected_state(token: str, started: float) -> tuple[float, dict[str, Any]]:
    deadline = started + 20
    latest: dict[str, Any] = {}
    while time.monotonic() < deadline:
        latest = _request("/v1/demo/scenarios/baltic-cable/status", token=token)
        if latest.get("state") == "failed":
            raise RuntimeError(f"Festival replay failed: {latest.get('error')}")
        if latest.get("state") == "completed" and all(latest.get(key) == value for key, value in EXPECTED.items()):
            return time.monotonic() - started, latest
        time.sleep(0.1)
    raise RuntimeError(f"Festival replay did not reach expected state: {latest}")


def main() -> None:
    token = _login()
    results: list[dict[str, Any]] = []
    for run_number in range(1, RUNS + 1):
        reset = _request("/v1/demo/scenarios/baltic-cable/reset", method="POST", token=token)
        if reset.get("state") != "idle":
            raise RuntimeError(f"Reset failed before run {run_number}: {reset}")
        started = time.monotonic()
        _request("/v1/demo/scenarios/baltic-cable/start", method="POST", token=token)
        latency, status = _wait_for_expected_state(token, started)
        results.append({"run": run_number, "latency_sec": round(latency, 3), "state": status})

    conservative_p95 = max(item["latency_sec"] for item in results)
    report = {
        "runs": results,
        "conservative_p95_sec": conservative_p95,
        "definition": "maximum of five standard-speed reset/replay measurements",
        "threshold_sec": MAX_LATENCY_SEC,
        "passed": conservative_p95 <= MAX_LATENCY_SEC,
    }
    OUTPUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    if not report["passed"]:
        raise SystemExit(f"Festival replay latency {conservative_p95:.3f}s exceeds {MAX_LATENCY_SEC:.3f}s")


if __name__ == "__main__":
    main()
