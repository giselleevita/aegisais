"""Shared pytest fixtures for API tests."""

import os

# Defaults so Sprint 1 production-style settings do not break the suite (see IMPLEMENTATION_PLAN.md).
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("WEBSOCKET_REQUIRE_AUTH", "false")

import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import Base, get_db
from app.modules.alerts.models import Alert  # noqa: F401 — register alerts for create_all
from app.modules.auth.models import (  # noqa: F401
    Organisation,
    PasswordResetToken,
    RefreshToken,
    User,
)
from app.modules.audit.models import AuditLog  # noqa: F401 — register audit_logs for create_all
from app.modules.integrations.models import (  # noqa: F401 — integration refs
    PortReference,
    UnlocodeReference,
)
from app.modules.itdae.models import ItdaeGeofenceZone  # noqa: F401 — itdae_geofence_zones
from app.modules.incidents.models import Incident  # noqa: F401 — incidents
from app.modules.vessels.models import (  # noqa: F401 — register for create_all
    VesselLatest,
    VesselPosition,
    WatchlistEntry,
)
from app.modules.billing.models import UsageLedgerEntry  # noqa: F401 — BL-010 billing ledger

# StaticPool: all sessions share one in-memory SQLite DB.
TEST_URL = "sqlite:///:memory:"
_engine = create_engine(
    TEST_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


def create_user_with_org(
    *,
    username: str,
    email: str,
    hashed_password: str,
    is_active: bool = True,
):
    """Insert User + Organisation (users.organisation_id is required)."""
    db = TestingSessionLocal()
    try:
        org = Organisation(
            name=f"org-{username}",
            slug=f"slug-{username}-{uuid.uuid4().hex[:8]}",
        )
        db.add(org)
        db.flush()
        user = User(
            username=username,
            email=email,
            hashed_password=hashed_password,
            role="viewer",
            organisation_id=org.id,
            is_active=is_active,
        )
        db.add(user)
        db.commit()
        return user
    finally:
        db.close()


@pytest.fixture(autouse=True)
def _reset_rate_limits_between_tests():
    """Avoid cross-test pollution (register/login limits) when many tests share one IP."""
    from app.middleware.rate_limit import reset_rate_limit_store

    reset_rate_limit_store()
    yield
    reset_rate_limit_store()


def _override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client():
    Base.metadata.create_all(bind=_engine)
    db = TestingSessionLocal()
    try:
        db.add(Organisation(id=1, name="Default", slug="default"))
        db.commit()
    finally:
        db.close()
    app.dependency_overrides[get_db] = _override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=_engine)


def register_and_login_as_admin(client: TestClient) -> str:
    """Register a user, promote to admin in the test DB, return Bearer token."""
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
        user.role = "admin"
        db.commit()
    finally:
        db.close()
    login = client.post(
        "/v1/auth/login",
        data={"username": u, "password": "p" * 12},
    )
    assert login.status_code == 200, login.text
    return login.json()["access_token"]
