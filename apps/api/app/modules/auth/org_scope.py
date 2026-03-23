"""Organisation scoping for multi-tenant queries (Sprint 4)."""

from __future__ import annotations

from typing import Any, Type, cast

from sqlalchemy.orm import Query

from app.modules.auth.models import User


def is_super_admin(user: User) -> bool:
    return cast(str, user.role) == "super_admin"


def apply_org_filter(query: Query, model: Type[Any], user: User) -> Query:
    """
    Restrict rows to the user's organisation.

    `super_admin` skips the filter so list/detail queries can span all organisations.
    Models must define `organisation_id` (integer FK).
    """
    if is_super_admin(user):
        return query
    if not hasattr(model, "organisation_id"):
        return query
    return query.filter(model.organisation_id == user.organisation_id)
