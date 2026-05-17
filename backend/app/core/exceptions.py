"""Sanitized application exceptions."""

from __future__ import annotations

from typing import Any


class SecurityException(Exception):
    """Tenant isolation or authorization violation — never expose internals."""

    def __init__(self, message: str = "Security policy violation"):
        super().__init__(message)
        self.public_message = "Access denied due to security policy."


class SolaceHTTPException(Exception):
    def __init__(self, status_code: int, detail: str, code: str | None = None):
        self.status_code = status_code
        self.detail = detail
        self.code = code
        super().__init__(detail)


class SetupRequiredException(SolaceHTTPException):
    def __init__(self, detail: str = "First-run setup is required"):
        super().__init__(503, detail, code="SETUP_REQUIRED")


class AccountLockedException(SolaceHTTPException):
    def __init__(self, locked_until: str):
        super().__init__(
            423,
            f"Account locked until {locked_until}",
            code="ACCOUNT_LOCKED",
        )
        self.locked_until = locked_until


def sanitize_error_detail(exc: Exception) -> dict[str, Any]:
    """Return client-safe error payload — no stack traces or secrets."""
    if isinstance(exc, SolaceHTTPException):
        payload: dict[str, Any] = {"detail": exc.detail}
        if exc.code:
            payload["code"] = exc.code
        return payload
    if isinstance(exc, SecurityException):
        return {"detail": exc.public_message, "code": "SECURITY_VIOLATION"}
    return {"detail": "An internal error occurred.", "code": "INTERNAL_ERROR"}
