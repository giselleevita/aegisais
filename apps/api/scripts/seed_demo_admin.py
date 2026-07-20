#!/usr/bin/env python3
"""Idempotently seed an admin account for non-production demo environments."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

from sqlalchemy.orm import Session

API_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_ROOT))

from app.core.config import settings  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.modules.auth.models import Organisation, User  # noqa: E402
from app.modules.auth.service import get_password_hash  # noqa: E402


def seed_demo_admin(
    db: Session,
    *,
    username: str,
    password: str,
    app_env: str,
) -> User:
    if app_env == "production":
        raise RuntimeError("Demo admin seeding is disabled in production")
    if not username.strip():
        raise ValueError("FESTIVAL_TEST_USERNAME is required")
    if len(password) < 12:
        raise ValueError("FESTIVAL_TEST_PASSWORD must contain at least 12 characters")

    organisation = db.query(Organisation).filter(Organisation.slug == "festival-demo").first()
    if organisation is None:
        organisation = Organisation(name="Festival Demo", slug="festival-demo")
        db.add(organisation)
        db.flush()

    user = db.query(User).filter(User.username == username).first()
    email_digest = hashlib.sha256(username.encode()).hexdigest()[:16]
    if user is None:
        user = User(
            username=username,
            email=f"festival-{email_digest}@invalid.example",
            hashed_password=get_password_hash(password),
            role="admin",
            organisation_id=organisation.id,
            is_active=True,
        )
        db.add(user)
    else:
        user.hashed_password = get_password_hash(password)
        user.role = "admin"
        user.organisation_id = organisation.id
        user.is_active = True
    db.commit()
    db.refresh(user)
    return user


def main() -> None:
    username = os.environ.get("FESTIVAL_TEST_USERNAME", "")
    password = os.environ.get("FESTIVAL_TEST_PASSWORD", "")
    with SessionLocal() as db:
        user = seed_demo_admin(
            db,
            username=username,
            password=password,
            app_env=settings.app_env,
        )
        print(json.dumps({"username": user.username, "role": user.role, "organisation_id": user.organisation_id}))


if __name__ == "__main__":
    main()
