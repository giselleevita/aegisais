from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, ConfigDict, EmailStr
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.modules.audit.services import AuditService
from app.modules.auth.models import Organisation, User
from app.modules.auth.service import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    issue_password_reset_token_for_email,
    notify_password_reset_delivery,
    password_reset_url,
    reset_password_with_token,
    revoke_access_token,
    revoke_refresh_token,
    verify_password,
    verify_refresh_token,
)
from app.middleware.rate_limit import (
    auth_forgot_password_rate_limit,
    auth_login_rate_limit,
    auth_register_rate_limit,
)

router = APIRouter()

security_bearer_optional = HTTPBearer(auto_error=False)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: Optional[str] = None


class UserCreate(BaseModel):
    username: str
    email: str
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    username: str
    email: str
    role: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class VerifyEmailRequest(BaseModel):
    token: str


def _refresh_cookie_secure() -> bool:
    return settings.app_env not in ("development", "test")


def _set_refresh_cookie(response: Response, raw_refresh: str) -> None:
    max_age = settings.refresh_token_expire_days * 86400
    response.set_cookie(
        key="refresh_token",
        value=raw_refresh,
        max_age=max_age,
        httponly=True,
        secure=_refresh_cookie_secure(),
        samesite="strict",
        path="/v1/auth",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        "refresh_token",
        path="/v1/auth",
        secure=_refresh_cookie_secure(),
        httponly=True,
        samesite="strict",
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    response: Response,
    _: Annotated[None, Depends(auth_login_rate_limit)],
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password"
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive"
        )

    access_token = create_access_token(data={"sub": user.username, "role": user.role})
    refresh_raw = create_refresh_token(user.id, db)
    user.last_login = datetime.now(timezone.utc)

    if settings.enable_audit_logging:
        AuditService.log_event(
            db,
            action="auth.login.success",
            change_summary=f"User logged in: {user.username}",
            organisation_id=user.organisation_id,
            user_id=user.username,
            resource_type="session",
        )
    db.commit()

    _set_refresh_cookie(response, refresh_raw)
    return {
        "access_token": access_token,
        "refresh_token": refresh_raw,
        "token_type": "bearer",
    }


@router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
    body: Annotated[Optional[RefreshRequest], Body()] = None,
):
    raw = (body.refresh_token if body else None) or request.cookies.get("refresh_token")
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing refresh token",
        )
    user = verify_refresh_token(raw, db)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    access_token = create_access_token(data={"sub": user.username, "role": user.role})
    user.last_login = datetime.now(timezone.utc)
    db.commit()

    _set_refresh_cookie(response, raw)
    return {
        "access_token": access_token,
        "refresh_token": raw,
        "token_type": "bearer",
    }


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        security_bearer_optional
    ),
):
    raw_refresh = request.cookies.get("refresh_token")
    if raw_refresh:
        revoke_refresh_token(raw_refresh, db)

    if credentials and credentials.credentials:
        revoke_access_token(credentials.credentials)

    db.commit()
    _clear_refresh_cookie(response)
    return {"ok": True}


@router.post("/forgot-password")
async def forgot_password(
    body: ForgotPasswordRequest,
    _: Annotated[None, Depends(auth_forgot_password_rate_limit)],
    db: Session = Depends(get_db),
):
    """Always returns 200 to avoid email enumeration. Rate limited per IP."""
    issued = issue_password_reset_token_for_email(body.email.strip(), db)
    if issued:
        to_email, raw = issued
        db.commit()
        notify_password_reset_delivery(to_email, password_reset_url(raw))
    else:
        db.commit()
    return {"ok": True}


@router.post("/reset-password")
async def reset_password(body: ResetPasswordRequest, db: Session = Depends(get_db)):
    ok = reset_password_with_token(body.token, body.new_password, db)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )
    return {"ok": True}


@router.post("/verify-email")
async def verify_email_stub(body: VerifyEmailRequest):
    """Placeholder for future email verification flow."""
    return {"status": "not_implemented", "token_received": bool(body.token)}


@router.post("/register", response_model=UserOut)
async def register(
    user_in: UserCreate,
    _: Annotated[None, Depends(auth_register_rate_limit)],
    db: Session = Depends(get_db),
):
    # Check if user exists
    if db.query(User).filter(User.username == user_in.username).first():
        raise HTTPException(status_code=400, detail="Username already registered")

    org = db.query(Organisation).filter(Organisation.slug == "default").first()
    if org is None:
        org = Organisation(name="Default", slug="default")
        db.add(org)
        db.flush()
    db_user = User(
        username=user_in.username,
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        role="viewer",
        organisation_id=org.id,
    )
    db.add(db_user)
    db.flush()
    if settings.enable_audit_logging:
        AuditService.log_event(
            db,
            action="auth.register",
            change_summary=f"New user registered: {db_user.username}",
            organisation_id=db_user.organisation_id,
            user_id=db_user.username,
            resource_type="user",
            resource_id=db_user.username,
        )
    db.commit()
    db.refresh(db_user)
    return db_user
