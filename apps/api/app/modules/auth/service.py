import hashlib
import secrets
import smtplib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from typing import Optional, cast

import bcrypt
import structlog
from jose import jwt  # type: ignore[import-untyped]
from prometheus_client import Counter
from sqlalchemy.orm import Session

from app.core.config import settings
from app.infrastructure.cache.redis_client import get_redis_client
from app.modules.auth.models import PasswordResetToken, RefreshToken, User

log = structlog.get_logger("aegisais.auth")

# BL-007: Prometheus counters for Redis-degraded auth paths.
# Alert on these counters so revocation outages are not silent.
_TOKEN_CHECK_DEGRADED = Counter(
    "aegisais_token_check_redis_degraded_total",
    "Token revocation checks skipped because Redis was unavailable (fail-open)",
)
_TOKEN_REVOKE_DEGRADED = Counter(
    "aegisais_token_revocation_redis_degraded_total",
    "Token revocations lost because Redis was unavailable",
)


def _as_utc_aware(dt: datetime) -> datetime:
    """SQLite may return naive datetimes for TIMESTAMP columns; normalize for comparisons."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception as e:
        log.error("password_verification_failed", error=str(e))
        return False


def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def _revoked_jti_key(jti: str) -> str:
    return f"{settings.redis_prefix}:revoked_jti:{jti}"


def _decode_jwt_signed(token: str, *, verify_exp: bool = True) -> Optional[dict]:
    try:
        return jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
            options={"verify_exp": verify_exp},
        )
    except jwt.JWTError:
        return None


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.access_token_expire_minutes)

    jti = secrets.token_urlsafe(16)
    to_encode.update({"exp": expire, "iat": now, "jti": jti})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    payload = _decode_jwt_signed(token)
    if payload is None:
        return None
    jti = payload.get("jti")
    if jti:
        try:
            r = get_redis_client()
            if r.exists(_revoked_jti_key(jti)):
                return None
        except Exception as e:
            # BL-007 fail-open policy: keep the API available when Redis is down.
            # Revocation is best-effort until Redis recovers.  The counter lets
            # ops alert on a sustained outage before tokens expire naturally.
            _TOKEN_CHECK_DEGRADED.inc()
            log.warning(
                "redis_unavailable_revocation_check_skipped",
                error=str(e),
            )
    return payload


def revoke_access_token(token: str) -> None:
    payload = _decode_jwt_signed(token)
    if payload is None:
        return
    jti = payload.get("jti")
    if not jti:
        return
    exp = payload.get("exp")
    if exp is None:
        return
    if isinstance(exp, datetime):
        exp_dt = exp if exp.tzinfo else exp.replace(tzinfo=timezone.utc)
    else:
        exp_dt = datetime.fromtimestamp(int(exp), tz=timezone.utc)
    now = datetime.now(timezone.utc)
    ttl_sec = int((exp_dt - now).total_seconds())
    if ttl_sec <= 0:
        return
    try:
        r = get_redis_client()
        r.setex(_revoked_jti_key(jti), ttl_sec, "1")
    except Exception as e:
        # BL-007: revocation write lost — token may remain valid until natural expiry.
        # Counter is wired to alert_rules.yml so ops are paged immediately.
        _TOKEN_REVOKE_DEGRADED.inc()
        log.warning("redis_unavailable_revoke_access_failed", error=str(e))


def create_refresh_token(user_id: int, db: Session) -> str:
    raw = secrets.token_urlsafe(64)
    token_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    row = RefreshToken(
        token_hash=token_hash,
        user_id=user_id,
        expires_at=expires_at,
        revoked=False,
    )
    db.add(row)
    db.flush()
    return raw


def verify_refresh_token(raw_token: str, db: Session) -> Optional[User]:
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    row = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
    if row is None or row.revoked:
        return None
    if _as_utc_aware(cast(datetime, row.expires_at)) <= datetime.now(timezone.utc):
        return None
    return db.query(User).filter(User.id == cast(int, row.user_id)).first()


def revoke_refresh_token(raw_token: str, db: Session) -> bool:
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    row = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
    if row is None:
        return False
    setattr(row, "revoked", True)
    db.flush()
    return True


def password_reset_url(raw_token: str) -> str:
    base = settings.password_reset_link_base.rstrip("/")
    return f"{base}/reset-password?token={raw_token}"


def _send_password_reset_smtp(to_email: str, reset_url: str) -> None:
    msg = EmailMessage()
    msg["Subject"] = "Password reset"
    msg["From"] = settings.email_from
    msg["To"] = to_email
    msg.set_content(
        f"You requested a password reset. Open this link to set a new password:\n\n{reset_url}\n\n"
        "If you did not request this, you can ignore this email."
    )
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
        smtp.starttls()
        if settings.smtp_user:
            smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(msg)


def notify_password_reset_delivery(to_email: str, reset_url: str) -> None:
    if settings.smtp_host.strip():
        try:
            _send_password_reset_smtp(to_email, reset_url)
        except Exception as e:
            log.error("password_reset_smtp_failed", error=str(e))
        return
    if settings.app_env in ("development", "test"):
        log.info("password_reset_link", reset_url=reset_url)
    else:
        log.warning(
            "password_reset_smtp_not_configured",
            hint="Set SMTP_HOST (and related) to send password reset emails in production.",
        )


def issue_password_reset_token_for_email(email: str, db: Session) -> Optional[tuple[str, str]]:
    """
    If a user exists, persist a new reset token (TTL from settings) and return (email, raw_token).
    Caller must commit. If no user, returns None.
    """
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        return None
    raw = secrets.token_urlsafe(48)
    token_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    expires_at = datetime.now(timezone.utc) + timedelta(
        hours=settings.password_reset_token_ttl_hours
    )
    row = PasswordResetToken(
        token_hash=token_hash,
        user_id=cast(int, user.id),
        expires_at=expires_at,
        used=False,
    )
    db.add(row)
    db.flush()
    return (cast(str, user.email), raw)


def verify_password_reset_token(raw_token: str, db: Session) -> Optional[PasswordResetToken]:
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    row = (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.token_hash == token_hash)
        .first()
    )
    if row is None or row.used:
        return None
    if _as_utc_aware(cast(datetime, row.expires_at)) <= datetime.now(timezone.utc):
        return None
    return row


def reset_password_with_token(raw_token: str, new_password: str, db: Session) -> bool:
    row = verify_password_reset_token(raw_token, db)
    if row is None:
        return False
    user = db.query(User).filter(User.id == cast(int, row.user_id)).first()
    if user is None or not user.is_active:
        return False
    setattr(user, "hashed_password", get_password_hash(new_password))
    setattr(row, "used", True)
    db.flush()
    db.commit()
    return True
