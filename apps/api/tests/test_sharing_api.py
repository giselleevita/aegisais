"""Sharing API access control and org-scoping behavior."""

from fastapi.testclient import TestClient

from app.modules.auth.models import User
from tests.conftest import TestingSessionLocal, register_and_login_as_admin


def _latest_user() -> User:
    db = TestingSessionLocal()
    try:
        user = db.query(User).filter(User.username.isnot(None)).order_by(User.id.desc()).first()
        assert user is not None
        db.expunge(user)
        return user
    finally:
        db.close()


def test_share_alert_requires_authentication(client: TestClient):
    response = client.post(
        "/v1/sharing/alerts",
        json={
            "alert_type": "TELEPORT",
            "severity": 75,
            "mmsi": "123456789",
            "summary": "allied share",
            "target_org_ids": [2],
            "share_reason": "coordination",
        },
    )

    assert response.status_code == 401


def test_share_alert_uses_authenticated_users_org_scope(client: TestClient):
    token = register_and_login_as_admin(client)
    actor = _latest_user()

    response = client.post(
        "/v1/sharing/alerts",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "alert_type": "TELEPORT",
            "severity": 75,
            "mmsi": "123456789",
            "summary": "allied share",
            "target_org_ids": [999],
            "share_reason": "coordination",
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["sharing_metadata"]["source_org_id"] == actor.organisation_id
    assert payload["sharing_metadata"]["target_org_ids"] == [999]


def test_cop_feed_requires_authenticated_viewer(client: TestClient):
    response = client.get("/v1/sharing/cop")
    assert response.status_code == 401


def test_cop_feed_allows_authenticated_viewer(client: TestClient):
    token = register_and_login_as_admin(client)

    response = client.get(
        "/v1/sharing/cop",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["feed_type"] == "COP"