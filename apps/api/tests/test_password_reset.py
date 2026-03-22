"""Password reset flow (TestClient + in-memory SQLite)."""

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.modules.auth.models import PasswordResetToken, User
from app.modules.auth.service import (
    issue_password_reset_token_for_email,
    verify_password_reset_token,
)


def _aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


from tests.conftest import TestingSessionLocal, create_user_with_org


def test_forgot_password_unknown_email_returns_200(client: TestClient):
    r = client.post("/v1/auth/forgot-password", json={"email": "nobody@example.com"})
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_forgot_password_creates_token_row(client: TestClient):
    create_user_with_org(username="pwuser", email="pwuser@example.com", hashed_password="x")

    r = client.post("/v1/auth/forgot-password", json={"email": "pwuser@example.com"})
    assert r.status_code == 200

    db = TestingSessionLocal()
    try:
        n = db.query(PasswordResetToken).count()
        assert n == 1
        row = db.query(PasswordResetToken).first()
        assert row is not None
        assert row.used is False
        assert _aware(row.expires_at) > datetime.now(timezone.utc)
    finally:
        db.close()


def test_reset_password_updates_password_and_marks_token_used(client: TestClient):
    create_user_with_org(
        username="resetme",
        email="resetme@example.com",
        hashed_password="oldhash",
    )
    db = TestingSessionLocal()
    try:
        issued = issue_password_reset_token_for_email("resetme@example.com", db)
        assert issued is not None
        _, raw = issued
        db.commit()
    finally:
        db.close()

    r = client.post(
        "/v1/auth/reset-password",
        json={"token": raw, "new_password": "newsecurepass12"},
    )
    assert r.status_code == 200
    assert r.json() == {"ok": True}

    db = TestingSessionLocal()
    try:
        row = db.query(PasswordResetToken).first()
        assert row is not None
        assert row.used is True
    finally:
        db.close()

    login_old = client.post(
        "/v1/auth/login",
        data={"username": "resetme", "password": "wrong"},
    )
    assert login_old.status_code == 401

    login_new = client.post(
        "/v1/auth/login",
        data={"username": "resetme", "password": "newsecurepass12"},
    )
    assert login_new.status_code == 200


def test_reset_password_rejects_invalid_token(client: TestClient):
    r = client.post(
        "/v1/auth/reset-password",
        json={"token": "not-a-valid-token", "new_password": "x" * 12},
    )
    assert r.status_code == 400
    assert "token" in r.json()["detail"].lower()


def test_reset_password_rejects_expired_token(client: TestClient):
    create_user_with_org(username="expired", email="expired@example.com", hashed_password="h")
    db = TestingSessionLocal()
    try:
        issued = issue_password_reset_token_for_email("expired@example.com", db)
        assert issued is not None
        _, raw = issued
        row = db.query(PasswordResetToken).first()
        assert row is not None
        row.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        db.commit()
    finally:
        db.close()

    r = client.post(
        "/v1/auth/reset-password",
        json={"token": raw, "new_password": "newsecurepass12"},
    )
    assert r.status_code == 400


def test_used_token_cannot_be_reused(client: TestClient):
    create_user_with_org(username="once", email="once@example.com", hashed_password="h")
    db = TestingSessionLocal()
    try:
        issued = issue_password_reset_token_for_email("once@example.com", db)
        assert issued is not None
        _, raw = issued
        db.commit()
    finally:
        db.close()

    first = client.post(
        "/v1/auth/reset-password",
        json={"token": raw, "new_password": "firstpass12345"},
    )
    assert first.status_code == 200

    second = client.post(
        "/v1/auth/reset-password",
        json={"token": raw, "new_password": "secondpass12345"},
    )
    assert second.status_code == 400


def test_forgot_password_rate_limit(client: TestClient):
    for _ in range(10):
        r = client.post("/v1/auth/forgot-password", json={"email": "a@b.com"})
        assert r.status_code == 200
    r = client.post("/v1/auth/forgot-password", json={"email": "a@b.com"})
    assert r.status_code == 429


def test_verify_email_stub(client: TestClient):
    r = client.post("/v1/auth/verify-email", json={"token": "any"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "not_implemented"
    assert body["token_received"] is True


def test_verify_password_reset_token_helper(client: TestClient):
    _ = client
    create_user_with_org(username="vrfy", email="vrfy@example.com", hashed_password="h")
    db = TestingSessionLocal()
    try:
        issued = issue_password_reset_token_for_email("vrfy@example.com", db)
        assert issued is not None
        _, raw = issued
        db.commit()
        row = verify_password_reset_token(raw, db)
        assert row is not None
    finally:
        db.close()
