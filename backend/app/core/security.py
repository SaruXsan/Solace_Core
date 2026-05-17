"""Password hashing and JWT helpers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from jose import JWTError, jwt
import bcrypt

# JWT signing derived from master key slice — not stored in DB
_ALGORITHM = "HS256"


def _jwt_secret() -> str:
    from app.core.config import get_master_key

    return get_master_key()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("ascii"))


def create_access_token(
    subject: str,
    organization_id: str,
    expires_minutes: int,
    extra: dict[str, Any] | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "org": organization_id,
        "iat": now,
        "exp": now + timedelta(minutes=expires_minutes),
        "type": "access",
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, _jwt_secret(), algorithm=_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, _jwt_secret(), algorithms=[_ALGORITHM])
    except JWTError as e:
        raise ValueError("Invalid or expired token") from e


def validate_password_strength(password: str) -> list[str]:
    errors: list[str] = []
    if len(password) < 12:
        errors.append("Password must be at least 12 characters")
    if not any(c.isupper() for c in password):
        errors.append("Password must include an uppercase letter")
    if not any(c.islower() for c in password):
        errors.append("Password must include a lowercase letter")
    if not any(c.isdigit() for c in password):
        errors.append("Password must include a digit")
    return errors
