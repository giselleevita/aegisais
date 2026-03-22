"""HTTP-level auth behavior (TestClient + in-memory SQLite)."""

from fastapi.testclient import TestClient

from app.modules.auth.models import User
from app.modules.auth.service import get_password_hash

from tests.conftest import TestingSessionLocal, create_user_with_org


def test_register_assigns_viewer_role(client: TestClient):
    r = client.post(
        "/v1/auth/register",
        json={
            "username": "alice",
            "email": "alice@example.com",
            "password": "secret123",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["role"] == "viewer"


def test_login_rejects_inactive_user(client: TestClient):
    create_user_with_org(
        username="bob",
        email="bob@example.com",
        hashed_password=get_password_hash("pw"),
        is_active=False,
    )

    r = client.post(
        "/v1/auth/login",
        data={"username": "bob", "password": "pw"},
    )
    assert r.status_code == 403
    assert "inactive" in r.json()["detail"].lower()


def test_bearer_rejected_after_user_deactivated(client: TestClient):
    create_user_with_org(
        username="dave",
        email="dave@example.com",
        hashed_password=get_password_hash("pw"),
        is_active=True,
    )

    login = client.post(
        "/v1/auth/login",
        data={"username": "dave", "password": "pw"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    db = TestingSessionLocal()
    try:
        u = db.query(User).filter(User.username == "dave").first()
        assert u is not None
        u.is_active = False
        db.commit()
    finally:
        db.close()

    r = client.get(
        "/v1/vessels",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 403
