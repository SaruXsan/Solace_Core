"""Request context for active executive consolidation scope (separate from operational scope)."""

from __future__ import annotations

import uuid
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ActiveConsolidationScope:
    id: uuid.UUID
    user_id: uuid.UUID
    scope_level: str
    country_id: uuid.UUID | None
    organization_id: uuid.UUID | None
    branch_id: uuid.UUID | None
    department_id: uuid.UUID | None
    include_child_scopes: bool
    max_classification_allowed: str
    can_view_raw_restricted: bool
    can_use_ai_summary: bool
    can_export: bool
    allowed_modules: list[str] | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "scope_level": self.scope_level,
            "country_id": str(self.country_id) if self.country_id else None,
            "organization_id": str(self.organization_id) if self.organization_id else None,
            "branch_id": str(self.branch_id) if self.branch_id else None,
            "department_id": str(self.department_id) if self.department_id else None,
            "include_child_scopes": self.include_child_scopes,
            "max_classification_allowed": self.max_classification_allowed,
            "can_view_raw_restricted": self.can_view_raw_restricted,
            "can_use_ai_summary": self.can_use_ai_summary,
            "can_export": self.can_export,
            "allowed_modules": self.allowed_modules,
        }


_active_consolidation: ContextVar[ActiveConsolidationScope | None] = ContextVar(
    "active_consolidation_scope", default=None
)


def set_active_consolidation_scope(scope: ActiveConsolidationScope | None) -> object:
    return _active_consolidation.set(scope)


def get_active_consolidation_scope() -> ActiveConsolidationScope | None:
    return _active_consolidation.get()


def reset_active_consolidation_scope(token: object) -> None:
    _active_consolidation.reset(token)
