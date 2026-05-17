"""Active enterprise scope context (country → company → branch → department)."""

from __future__ import annotations

import contextvars
from dataclasses import dataclass
from typing import Optional
from uuid import UUID

_active_scope: contextvars.ContextVar[Optional["ActiveScope"]] = contextvars.ContextVar(
    "active_scope", default=None
)


@dataclass(frozen=True)
class ActiveScope:
    scope_type: str
    country_id: UUID | None
    organization_id: UUID | None
    branch_id: UUID | None
    department_id: UUID | None

    def to_dict(self) -> dict:
        return {
            "scope_type": self.scope_type,
            "country_id": str(self.country_id) if self.country_id else None,
            "organization_id": str(self.organization_id) if self.organization_id else None,
            "branch_id": str(self.branch_id) if self.branch_id else None,
            "department_id": str(self.department_id) if self.department_id else None,
        }


def set_active_scope(scope: ActiveScope | None) -> contextvars.Token:
    return _active_scope.set(scope)


def get_active_scope() -> ActiveScope | None:
    return _active_scope.get()


def reset_active_scope(token: contextvars.Token) -> None:
    _active_scope.reset(token)


def require_active_organization_id() -> UUID:
    from app.core.exceptions import SecurityException
    from app.core.tenant_context import get_organization_id, is_system_bypass

    if is_system_bypass():
        org = get_organization_id()
        if org:
            return org
        raise SecurityException("System bypass requires explicit organization context")
    scope = get_active_scope()
    if scope and scope.organization_id:
        return scope.organization_id
    org = get_organization_id()
    if org:
        return org
    raise SecurityException("No active company scope for tenant isolation")
