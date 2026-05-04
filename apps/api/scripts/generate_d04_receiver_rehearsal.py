#!/usr/bin/env python3
"""Generate repo-backed receiver rehearsal evidence for D-04 interoperability."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

from fastapi.testclient import TestClient

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("WEBSOCKET_REQUIRE_AUTH", "false")
os.environ.setdefault("LLM_ENABLED", "false")
os.environ.pop("LLM_API_KEY", None)

SCRIPT_DIR = Path(__file__).resolve().parent
API_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(API_DIR))

from app.main import app  # noqa: E402


NFFI_NS = {"nffi": "urn:nato:stanag:5527:nffi:1:0"}
EVIDENCE_DIR = API_DIR / "docs" / "evidence"


def _write_text(name: str, content: str) -> Path:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    output_file = EVIDENCE_DIR / name
    output_file.write_text(content)
    return output_file


def _cot_summary(root: ET.Element) -> dict[str, object]:
    point = root.find("point")
    detail = root.find("detail")
    contact = detail.find("contact") if detail is not None else None
    return {
        "root_tag": root.tag,
        "uid": root.get("uid"),
        "event_type": root.get("type"),
        "lat": point.get("lat") if point is not None else None,
        "lon": point.get("lon") if point is not None else None,
        "callsign": contact.get("callsign") if contact is not None else None,
    }


def _nffi_summary(root: ET.Element) -> dict[str, object]:
    header = root.find("nffi:MessageHeader", NFFI_NS)
    track_number = root.find(".//nffi:TrackNumber", NFFI_NS)
    return {
        "root_tag": root.tag,
        "schema_version": root.get("schemaVersion"),
        "sender_id": header.findtext("nffi:SenderID", default=None, namespaces=NFFI_NS)
        if header is not None else None,
        "message_id": header.findtext("nffi:MessageID", default=None, namespaces=NFFI_NS)
        if header is not None else None,
        "track_number": track_number.text if track_number is not None else None,
    }


CASES = [
    {
        "name": "cot_vessel",
        "url": "/v1/interop/cot/vessel/123456789",
        "params": {
            "lat": 60.1234,
            "lon": 20.5678,
            "sog": 12.5,
            "cog": 45.0,
            "vessel_name": "TEST-VESSEL-AEGIS",
        },
        "receiver": "TAK Server / ATAK",
        "expected_root": "event",
        "summary": _cot_summary,
    },
    {
        "name": "cot_alert",
        "url": "/v1/interop/cot/alert/7",
        "params": {
            "alert_type": "identity_spoofing",
            "severity": 3,
            "mmsi": "123456789",
            "lat": 60.1234,
            "lon": 20.5678,
            "summary": "AIS identity inconsistency detected",
        },
        "receiver": "TAK Server / ATAK",
        "expected_root": "event",
        "summary": _cot_summary,
    },
    {
        "name": "nffi_vessel",
        "url": "/v1/interop/nffi/vessel/123456789",
        "params": {
            "lat": 60.1234,
            "lon": 20.5678,
            "sog": 12.5,
            "cog": 45.0,
            "vessel_name": "TEST-VESSEL-AEGIS",
            "imo": "1234567",
            "flag_state": "SE",
        },
        "receiver": "NATO C2 / NFFI consumers",
        "expected_root": f"{{{NFFI_NS['nffi']}}}NFCIMessage",
        "summary": _nffi_summary,
    },
    {
        "name": "nffi_alert",
        "url": "/v1/interop/nffi/alert/7",
        "params": {
            "alert_type": "identity_spoofing",
            "severity": 3,
            "mmsi": "123456789",
            "lat": 60.1234,
            "lon": 20.5678,
            "summary": "AIS identity inconsistency detected",
        },
        "receiver": "NATO C2 / NFFI consumers",
        "expected_root": f"{{{NFFI_NS['nffi']}}}NFCIMessage",
        "summary": _nffi_summary,
    },
]


def main() -> int:
    results: list[dict[str, object]] = []

    with TestClient(app) as client:
        for case in CASES:
            response = client.get(case["url"], params=case["params"])
            response.raise_for_status()
            content_type = response.headers.get("content-type", "")
            if not content_type.startswith("application/xml"):
                raise RuntimeError(f"Unexpected content-type for {case['name']}: {content_type}")

            root = ET.fromstring(response.text)
            if root.tag != case["expected_root"]:
                raise RuntimeError(
                    f"Unexpected root tag for {case['name']}: {root.tag} != {case['expected_root']}"
                )

            xml_path = _write_text(f"d04_receiver_rehearsal_{case['name']}.xml", response.text)
            results.append(
                {
                    "name": case["name"],
                    "receiver": case["receiver"],
                    "url": case["url"],
                    "status_code": response.status_code,
                    "content_type": content_type,
                    "artifact": xml_path.name,
                    "checks": {
                        "route_reachable": True,
                        "xml_parseable": True,
                        "receiver_shape_verified": True,
                    },
                    "summary": case["summary"](root),
                }
            )

    manifest = {
        "status": "pass",
        "mode": "repo-backed receiver rehearsal",
        "note": (
            "This package verifies AegisAIS interop routes and receiver-facing XML structure in a lab "
            "rehearsal. External TAK Server / NATO receiver confirmation remains a separate field activity."
        ),
        "artifacts": results,
    }
    manifest_path = _write_text(
        "d04_receiver_rehearsal_manifest.json",
        json.dumps(manifest, indent=2),
    )

    print(f"✅ Generated: {manifest_path}")
    for result in results:
        print(f"✅ Rehearsed: {result['artifact']} via {result['url']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())