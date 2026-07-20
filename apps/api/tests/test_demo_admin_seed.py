import pytest

from app.modules.auth.models import User
from scripts.seed_demo_admin import seed_demo_admin
from tests.conftest import TestingSessionLocal


def test_demo_admin_seed_is_idempotent(client):
    with TestingSessionLocal() as db:
        first = seed_demo_admin(
            db,
            username="festival-ci",
            password="festival-ci-password",
            app_env="test",
        )
        first_id = first.id
        second = seed_demo_admin(
            db,
            username="festival-ci",
            password="festival-ci-password-updated",
            app_env="test",
        )
        assert second.id == first_id
        assert second.role == "admin"
        assert second.is_active is True
        assert db.query(User).filter(User.username == "festival-ci").count() == 1


def test_demo_admin_seed_refuses_production(client):
    with TestingSessionLocal() as db, pytest.raises(RuntimeError, match="disabled in production"):
        seed_demo_admin(
            db,
            username="festival-ci",
            password="festival-ci-password",
            app_env="production",
        )
