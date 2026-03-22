"""Integration-style tests for admin upload and replay endpoints."""

import uuid
from io import BytesIO

import pytest
import zstandard as zstd
from fastapi.testclient import TestClient

import app.api.v1.upload as upload_module
from app.modules.audit.models import AuditLog
from tests.conftest import TestingSessionLocal
from app.core.config import settings
from app.infrastructure.ingest.replay import replay_state
from tests.conftest import register_and_login_as_admin


@pytest.fixture(autouse=True)
def reset_replay_state():
    replay_state.running = False
    replay_state.stop_requested = False
    yield


def _viewer_token(client: TestClient) -> str:
    u = f"v_{uuid.uuid4().hex[:12]}"
    r = client.post(
        "/v1/auth/register",
        json={"username": u, "email": f"{u}@test.local", "password": "p" * 12},
    )
    assert r.status_code == 200, r.text
    login = client.post(
        "/v1/auth/login",
        data={"username": u, "password": "p" * 12},
    )
    assert login.status_code == 200, login.text
    return login.json()["access_token"]


def test_upload_csv_succeeds_for_admin(client: TestClient, tmp_path, monkeypatch):
    monkeypatch.setattr(upload_module, "DATA_RAW_DIR", tmp_path)
    token = register_and_login_as_admin(client)
    body = b"mmsi,timestamp,lat,lon\n123456789,1700000000,55.0,12.0\n"
    r = client.post(
        "/v1/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("smoke.csv", BytesIO(body), "text/csv")},
    )
    assert r.status_code == 200, r.text
    assert r.json()["filename"] == "smoke.csv"
    assert (tmp_path / "smoke.csv").exists()
    db = TestingSessionLocal()
    try:
        row = (
            db.query(AuditLog)
            .filter(AuditLog.action == "upload.file.success")
            .filter(AuditLog.resource_id == "smoke.csv")
            .first()
        )
        assert row is not None
        assert row.details.get("size_bytes") == len(body)
    finally:
        db.close()


def test_upload_csv_rejects_missing_required_columns(
    client: TestClient, tmp_path, monkeypatch
):
    monkeypatch.setattr(upload_module, "DATA_RAW_DIR", tmp_path)
    token = register_and_login_as_admin(client)
    body = b"foo,bar\n1,2\n"
    r = client.post(
        "/v1/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("bad.csv", BytesIO(body), "text/csv")},
    )
    assert r.status_code == 400
    assert "Missing required columns" in r.json()["detail"]


def test_upload_csv_accepts_column_aliases(client: TestClient, tmp_path, monkeypatch):
    monkeypatch.setattr(upload_module, "DATA_RAW_DIR", tmp_path)
    token = register_and_login_as_admin(client)
    body = (
        b"latitude,longitude,mmsi,timestamp\n"
        b"55.0,12.0,123456789,1700000000\n"
    )
    r = client.post(
        "/v1/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("alias.csv", BytesIO(body), "text/csv")},
    )
    assert r.status_code == 200, r.text


def test_upload_zst_succeeds_for_admin(client: TestClient, tmp_path, monkeypatch):
    monkeypatch.setattr(upload_module, "DATA_RAW_DIR", tmp_path)
    token = register_and_login_as_admin(client)
    plain = b"mmsi,timestamp,lat,lon\n123456789,1700000000,55.0,12.0\n"
    comp = zstd.ZstdCompressor().compress(plain)
    r = client.post(
        "/v1/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("smoke.csv.zst", BytesIO(comp), "application/octet-stream")},
    )
    assert r.status_code == 200, r.text
    assert (tmp_path / "smoke.csv.zst").exists()


def test_upload_forbidden_for_viewer(client: TestClient, tmp_path, monkeypatch):
    monkeypatch.setattr(upload_module, "DATA_RAW_DIR", tmp_path)
    token = _viewer_token(client)
    r = client.post(
        "/v1/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("x.csv", BytesIO(b"mmsi,timestamp,lat,lon\n1,1,1,1\n"), "text/csv")},
    )
    assert r.status_code == 403


def test_replay_start_succeeds_with_valid_file(
    client: TestClient, tmp_path, monkeypatch
):
    monkeypatch.setattr(settings, "allow_replay", True)
    csv_path = tmp_path / "replay_smoke.csv"
    csv_path.write_text(
        "mmsi,timestamp,lat,lon\n123456789,1700000000,55.0,12.0\n",
        encoding="utf-8",
    )
    token = register_and_login_as_admin(client)
    r = client.post(
        "/v1/replay/start",
        params={"path": str(csv_path.resolve()), "speedup": 10000.0},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "started"
    assert data["path"] == str(csv_path.resolve())


def test_replay_start_returns_404_when_file_missing(
    client: TestClient, tmp_path, monkeypatch
):
    monkeypatch.setattr(settings, "allow_replay", True)
    token = register_and_login_as_admin(client)
    missing = tmp_path / "does_not_exist.csv"
    r = client.post(
        "/v1/replay/start",
        params={"path": str(missing.resolve())},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404


def test_replay_start_forbidden_when_disabled(client: TestClient, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "allow_replay", False)
    csv_path = tmp_path / "x.csv"
    csv_path.write_text("mmsi,timestamp,lat,lon\n1,1700000000,1.0,2.0\n")
    token = register_and_login_as_admin(client)
    r = client.post(
        "/v1/replay/start",
        params={"path": str(csv_path.resolve())},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403


def test_replay_status_requires_auth(client: TestClient):
    r = client.get("/v1/replay/status")
    assert r.status_code == 401


def test_replay_status_ok_when_authenticated(client: TestClient):
    token = _viewer_token(client)
    r = client.get(
        "/v1/replay/status",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert "running" in body
    assert "processed" in body
