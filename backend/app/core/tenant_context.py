"""Active organization context for tenant isolation safety fuse."""

from __future__ import annotations

import contextvars
from dataclasses import dataclass
from typing import Optional
from uuid import UUID

_current_org: contextvars.ContextVar[Optional[UUID]] = contextvars.ContextVar(
    "organization_id", default=None
)
_system_bypass: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "tenant_system_bypass", default=False
)


@dataclass(frozen=True)
class TenantContext:
    organization_id: UUID
    user_id: UUID | None = None
    is_system_job: bool = False


def set_organization_id(org_id: UUID | None) -> contextvars.Token:
    return _current_org.set(org_id)


def get_organization_id() -> UUID | None:
    return _current_org.get()


def reset_organization_id(token: contextvars.Token) -> None:
    _current_org.reset(token)


def enable_system_bypass(audited_reason: str = "") -> contextvars.Token:
    """Allow controlled system jobs to bypass tenant fuse — must be audited."""
    _ = audited_reason
    return _system_bypass.set(True)


def is_system_bypass() -> bool:
    return _system_bypass.get()


def reset_system_bypass(token: contextvars.Token) -> None:
    _system_bypass.reset(token)


def require_organization_context() -> UUID:
    from app.core.exceptions import SecurityException

    if is_system_bypass():
        raise SecurityException("System bypass active without explicit org — invalid state")
    org_id = get_organization_id()
    if org_id is None:
        raise SecurityException(
            "Tenant-scoped query blocked: no active organization context"
        )
    return org_id
