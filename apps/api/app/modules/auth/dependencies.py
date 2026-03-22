from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.auth.models import User
from app.modules.auth.service import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/auth/login")

# Role names (Sprint 4)
ROLE_VIEWER = "viewer"
ROLE_ANALYST = "analyst"
ROLE_ADMIN = "admin"
ROLE_SUPER_ADMIN = "super_admin"


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    username: str = payload.get("sub")
    if username is None:
        raise credentials_exception

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def get_org_scope(current_user: User = Depends(get_current_user)) -> User:
    """Authenticated user with `organisation_id` loaded for org-scoped list/detail handlers."""
    return current_user


def require_viewer_or_above(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in (
        ROLE_VIEWER,
        ROLE_ANALYST,
        ROLE_ADMIN,
        ROLE_SUPER_ADMIN,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )
    return current_user


def require_analyst(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in (ROLE_ANALYST, ROLE_ADMIN, ROLE_SUPER_ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Analyst role or higher required",
        )
    return current_user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in (ROLE_ADMIN, ROLE_SUPER_ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user


def require_role(role: str):
    """
    Deprecated: prefer `require_analyst` / `require_admin` / `require_viewer_or_above`.
    Kept for backward compatibility with modules that expect role(name).
    """

    def role_checker(current_user: User = Depends(get_current_user)):
        if role == ROLE_ANALYST:
            if current_user.role not in (ROLE_ANALYST, ROLE_ADMIN, ROLE_SUPER_ADMIN):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Analyst role or higher required",
                )
            return current_user
        if current_user.role not in (role, ROLE_ADMIN, ROLE_SUPER_ADMIN):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions",
            )
        return current_user

    return role_checker
