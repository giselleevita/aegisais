"""TOTP-based MFA for auth module (GAP-10).

Implements RFC 6238 TOTP (Time-based One-Time Password) for multi-factor
authentication.  Uses the pyotp library.

Flow:
1. User enables MFA → generates secret + QR URI
2. User confirms with a TOTP code → MFA activated
3. Login requires TOTP code after password verification
"""

from __future__ import annotations

import logging

_log = logging.getLogger("aegisais.auth.mfa")

# Attempt to import pyotp; gracefully degrade if not installed
try:
    import pyotp
    HAS_PYOTP = True
except ImportError:
    HAS_PYOTP = False
    _log.warning("pyotp not installed — MFA disabled. Install: pip install pyotp")


def generate_totp_secret() -> str:
    """Generate a new TOTP secret for a user."""
    if not HAS_PYOTP:
        raise RuntimeError("pyotp not installed — cannot generate MFA secret")
    return pyotp.random_base32()


def get_provisioning_uri(
    secret: str,
    username: str,
    issuer: str = "AegisAIS",
) -> str:
    """Generate an otpauth:// URI for QR code display."""
    if not HAS_PYOTP:
        raise RuntimeError("pyotp not installed")
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=username, issuer_name=issuer)


def verify_totp(secret: str, code: str) -> bool:
    """Verify a TOTP code against a secret.

    Allows 1-step time drift (valid_window=1) to accommodate clock skew.
    """
    if not HAS_PYOTP:
        _log.error("pyotp not installed — MFA verification unavailable")
        return False
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)


def is_mfa_available() -> bool:
    """Check if MFA dependencies are installed."""
    return HAS_PYOTP
