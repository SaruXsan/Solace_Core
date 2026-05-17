"""Runtime configuration — only SOLACE_MASTER_KEY is allowed from the environment."""

from __future__ import annotations

import os
import sys
from functools import lru_cache

MASTER_KEY_ENV = "SOLACE_MASTER_KEY"
MIN_MASTER_KEY_LEN = 32


class MasterKeyError(RuntimeError):
    """Raised when SOLACE_MASTER_KEY is missing or too weak."""


def require_master_key() -> str:
    """Enforce SOLACE_MASTER_KEY at startup. App must not run without it."""
    key = os.environ.get(MASTER_KEY_ENV, "").strip()
    if not key:
        print(
            f"FATAL: {MASTER_KEY_ENV} is not set. "
            "Solace Enterprise Core refuses to start without the master encryption key.",
            file=sys.stderr,
        )
        raise MasterKeyError(f"{MASTER_KEY_ENV} is required")
    if len(key) < MIN_MASTER_KEY_LEN:
        print(
            f"FATAL: {MASTER_KEY_ENV} must be at least {MIN_MASTER_KEY_LEN} characters.",
            file=sys.stderr,
        )
        raise MasterKeyError(f"{MASTER_KEY_ENV} is too short")
    return key


@lru_cache(maxsize=1)
def get_master_key() -> str:
    return require_master_key()


class AppSettings:
    """Non-secret runtime flags (loaded after DB bootstrap)."""

    app_name: str = "Solace Enterprise Core"
    app_version: str = "0.1.0-foundation"
    api_prefix: str = "/api/v1"
    # Defaults until Core_Settings overrides
    session_timeout_minutes: int = 480
    token_expiry_minutes: int = 480
    login_max_attempts: int = 5
    login_lockout_minutes: int = 5
    mfa_otp_expiry_minutes: int = 10
    mfa_otp_max_attempts: int = 5
    mfa_resend_cooldown_seconds: int = 60


settings = AppSettings()
