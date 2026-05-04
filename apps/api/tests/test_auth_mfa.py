from fastapi.testclient import TestClient

from app.modules.auth.models import User

from tests.conftest import TestingSessionLocal


def _register(client: TestClient, username: str, password: str = "p" * 12) -> None:
    response = client.post(
        "/v1/auth/register",
        json={"username": username, "email": f"{username}@test.local", "password": password},
    )
    assert response.status_code == 200, response.text


def _login(client: TestClient, username: str, password: str = "p" * 12, otp: str | None = None):
    data = {"username": username, "password": password}
    if otp is not None:
        data["otp"] = otp
    return client.post("/v1/auth/login", data=data)


def test_mfa_setup_enable_and_login_requires_otp(client: TestClient):
    from app.modules.auth.mfa import is_mfa_available

    if not is_mfa_available():
        return

    import pyotp

    username = "mfa_user"
    _register(client, username)
    login = _login(client, username)
    token = login.json()["access_token"]

    setup = client.post(
        "/v1/auth/mfa/setup",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert setup.status_code == 200, setup.text
    body = setup.json()
    assert body["pending_setup"] is True
    assert body["enabled"] is False
    assert body["secret"]
    assert body["provisioning_uri"].startswith("otpauth://")

    code = pyotp.TOTP(body["secret"]).now()
    enable = client.post(
        "/v1/auth/mfa/enable",
        json={"code": code},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert enable.status_code == 200, enable.text

    without_otp = _login(client, username)
    assert without_otp.status_code == 401
    assert "mfa code required" in without_otp.json()["detail"].lower()

    wrong_otp = _login(client, username, otp="000000")
    assert wrong_otp.status_code == 401

    fresh_code = pyotp.TOTP(body["secret"]).now()
    with_otp = _login(client, username, otp=fresh_code)
    assert with_otp.status_code == 200, with_otp.text
    assert with_otp.json()["access_token"]


def test_mfa_disable_clears_secret_and_allows_password_only_login(client: TestClient):
    from app.modules.auth.mfa import is_mfa_available

    if not is_mfa_available():
        return

    import pyotp

    username = "mfa_disable_user"
    password = "p" * 12
    _register(client, username, password=password)
    base_login = _login(client, username, password=password)
    token = base_login.json()["access_token"]

    setup = client.post(
        "/v1/auth/mfa/setup",
        headers={"Authorization": f"Bearer {token}"},
    )
    secret = setup.json()["secret"]
    code = pyotp.TOTP(secret).now()
    enable = client.post(
        "/v1/auth/mfa/enable",
        json={"code": code},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert enable.status_code == 200, enable.text

    current_code = pyotp.TOTP(secret).now()
    disable = client.post(
        "/v1/auth/mfa/disable",
        json={"password": password, "code": current_code},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert disable.status_code == 200, disable.text

    db = TestingSessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        assert user is not None
        assert user.mfa_enabled is False
        assert user.totp_secret is None
    finally:
        db.close()

    login = _login(client, username, password=password)
    assert login.status_code == 200, login.text


def test_mfa_status_reflects_pending_and_enabled_state(client: TestClient):
    from app.modules.auth.mfa import is_mfa_available

    if not is_mfa_available():
        return

    import pyotp

    username = "mfa_status_user"
    _register(client, username)
    login = _login(client, username)
    token = login.json()["access_token"]

    initial = client.get(
        "/v1/auth/mfa/status",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert initial.status_code == 200
    assert initial.json()["enabled"] is False
    assert initial.json()["pending_setup"] is False

    setup = client.post(
        "/v1/auth/mfa/setup",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert setup.status_code == 200

    pending = client.get(
        "/v1/auth/mfa/status",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert pending.json()["pending_setup"] is True

    code = pyotp.TOTP(setup.json()["secret"]).now()
    enable = client.post(
        "/v1/auth/mfa/enable",
        json={"code": code},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert enable.status_code == 200

    enabled = client.get(
        "/v1/auth/mfa/status",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert enabled.json()["enabled"] is True
    assert enabled.json()["pending_setup"] is False