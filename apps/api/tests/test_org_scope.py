"""Multi-tenant org isolation (Sprint 4 Task 4.1) and role checks."""

import uuid
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.modules.alerts.models import Alert
from app.modules.auth.models import Organisation, User
from tests.conftest import TestingSessionLocal


def _register_analyst_token(client: TestClient) -> str:
    u = f"u_{uuid.uuid4().hex[:12]}"
    assert (
        client.post(
            "/v1/auth/register",
            json={"username": u, "email": f"{u}@t.local", "password": "p" * 12},
        ).status_code
        == 200
    )
    db = TestingSessionLocal()
    try:
        user = db.query(User).filter(User.username == u).first()
        assert user is not None
        user.role = "analyst"
        db.commit()
    finally:
        db.close()
    login = client.post(
        "/v1/auth/login",
        data={"username": u, "password": "p" * 12},
    )
    assert login.status_code == 200
    return login.json()["access_token"]


def test_alerts_scoped_to_user_organisation(client: TestClient):
    tok = _register_analyst_token(client)
    db = TestingSessionLocal()
    try:
        org2 = Organisation(name="Other tenant", slug=f"other-{uuid.uuid4().hex[:8]}")
        db.add(org2)
        db.flush()
        db.add(
            Alert(
                organisation_id=org2.id,
                timestamp=datetime(2025, 3, 1, tzinfo=timezone.utc),
                mmsi="111111111",
                type="TELEPORT",
                severity=50,
                summary="other org",
                evidence={},
                status="new",
            )
        )
        db.add(
            Alert(
                organisation_id=1,
                timestamp=datetime(2025, 3, 2, tzinfo=timezone.utc),
                mmsi="222222222",
                type="TELEPORT",
                severity=50,
                summary="default org",
                evidence={},
                status="new",
            )
        )
        db.commit()
    finally:
        db.close()

    r = client.get("/v1/alerts", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["summary"] == "default org"


def test_super_admin_sees_alerts_across_organisations(client: TestClient):
    u = f"a_{uuid.uuid4().hex[:12]}"
    r = client.post(
        "/v1/auth/register",
        json={"username": u, "email": f"{u}@test.local", "password": "p" * 12},
    )
    assert r.status_code == 200, r.text
    db = TestingSessionLocal()
    try:
        user = db.query(User).filter(User.username == u).first()
        assert user is not None
        user.role = "super_admin"
        db.commit()
    finally:
        db.close()
    login = client.post(
        "/v1/auth/login",
        data={"username": u, "password": "p" * 12},
    )
    assert login.status_code == 200
    super_tok = login.json()["access_token"]

    db = TestingSessionLocal()
    try:
        org2 = Organisation(name="Other tenant 2", slug=f"o2-{uuid.uuid4().hex[:8]}")
        db.add(org2)
        db.flush()
        db.add(
            Alert(
                organisation_id=org2.id,
                timestamp=datetime(2025, 4, 1, tzinfo=timezone.utc),
                mmsi="333333333",
                type="TELEPORT",
                severity=50,
                summary="super sees",
                evidence={},
                status="new",
            )
        )
        db.commit()
    finally:
        db.close()

    r = client.get("/v1/alerts", headers={"Authorization": f"Bearer {super_tok}"})
    assert r.status_code == 200
    summaries = {x["summary"] for x in r.json()}
    assert "super sees" in summaries
