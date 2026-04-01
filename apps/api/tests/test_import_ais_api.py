"""Tests for /v1/import/ais batch import endpoint."""

from fastapi.testclient import TestClient

from tests.conftest import register_and_login_as_admin


def test_import_ais_requires_auth(client: TestClient):
    payload = {
        "records": [
            {
                "mmsi": "123456789",
                "latitude": 55.6,
                "longitude": 12.6,
            }
        ]
    }
    r = client.post("/v1/import/ais", json=payload)
    assert r.status_code == 401


def test_import_ais_accepts_batch_for_admin(client: TestClient):
    token = register_and_login_as_admin(client)
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "records": [
            {
                "mmsi": "123456789",
                "latitude": 55.6001,
                "longitude": 12.6001,
                "speed": 12.5,
                "course": 180.0,
                "vessel_name": "Pilot Vessel",
            },
            {
                "mmsi": "987654321",
                "latitude": 56.1002,
                "longitude": 11.9002,
                "speed": 9.2,
            },
        ]
    }
    r = client.post("/v1/import/ais", json=payload, headers=headers)
    assert r.status_code == 207
    body = r.json()
    assert body["imported"] == 2
    assert body["skipped"] == 0


def test_import_ais_skips_invalid_mmsi_rows(client: TestClient):
    token = register_and_login_as_admin(client)
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "records": [
            {
                "mmsi": "123456789",
                "latitude": 55.0,
                "longitude": 12.0,
            },
            {
                "mmsi": "bad-mmsi",
                "latitude": 55.1,
                "longitude": 12.1,
            },
        ]
    }
    r = client.post("/v1/import/ais", json=payload, headers=headers)
    # Validation fails before endpoint loop for non-digit MMSI.
    assert r.status_code == 422
