"""SMTP path for password reset (mocked smtplib — no real mail server)."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from tests.conftest import create_user_with_org


@pytest.fixture
def smtp_user(client: TestClient):
    create_user_with_org(
        username="smtpuser",
        email="smtpuser@example.com",
        hashed_password="x",
    )
    return "smtpuser@example.com"


def test_forgot_password_invokes_smtp_when_configured(
    client: TestClient, smtp_user: str, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(settings, "smtp_host", "127.0.0.1")
    monkeypatch.setattr(settings, "smtp_port", 587)
    monkeypatch.setattr(settings, "smtp_user", "")
    monkeypatch.setattr(settings, "smtp_password", "")
    monkeypatch.setattr(settings, "email_from", "noreply@aegisais.test")

    mock_ctx = MagicMock()
    mock_smtp_class = MagicMock(return_value=mock_ctx)
    mock_ctx.__enter__.return_value = mock_ctx
    mock_ctx.__exit__.return_value = None

    with patch("app.modules.auth.service.smtplib.SMTP", mock_smtp_class):
        r = client.post("/v1/auth/forgot-password", json={"email": smtp_user})
    assert r.status_code == 200
    assert r.json() == {"ok": True}

    mock_smtp_class.assert_called_once_with("127.0.0.1", 587, timeout=30)
    mock_ctx.starttls.assert_called_once()
    mock_ctx.send_message.assert_called_once()
    sent = mock_ctx.send_message.call_args[0][0]
    assert smtp_user in (sent["To"] or sent.get("To"))


def test_forgot_password_smtp_failure_still_returns_200(
    client: TestClient, smtp_user: str, monkeypatch: pytest.MonkeyPatch
):
    """Enumeration-safe: route returns 200 even if SMTP raises."""
    monkeypatch.setattr(settings, "smtp_host", "127.0.0.1")
    monkeypatch.setattr(settings, "smtp_port", 587)
    monkeypatch.setattr(settings, "email_from", "noreply@aegisais.test")

    with patch("app.modules.auth.service.smtplib.SMTP") as mock_smtp:
        mock_smtp.side_effect = OSError("connection refused")

        r = client.post("/v1/auth/forgot-password", json={"email": smtp_user})
    assert r.status_code == 200
    assert r.json() == {"ok": True}
