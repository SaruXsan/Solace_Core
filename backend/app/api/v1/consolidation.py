"""Executive consolidation scope API (foundation — no reports)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_configured_db, require_permission
from app.core.exceptions import SolaceHTTPException
from app.models.platform import CoreConsolidationScope, CoreUser
from app.services import consolidation_scope_service as css

router = APIRouter(prefix="/consolidation", tags=["consolidation"])


class ConsolidationScopeIn(BaseModel):
    user_id: uuid.UUID
    name: str
    description: str | None = None
    country_id: uuid.UUID | None = None
    organization_id: uuid.UUID | None = None
    branch_id: uuid.UUID | None = None
    department_id: uuid.UUID | None = None
    scope_level: str
    include_child_scopes: bool = True
    allowed_modules: list[str] | None = None
    max_classification_allowed: str = "Internal"
    can_view_raw_restricted: bool = False
    can_use_ai_summary: bool = False
    can_export: bool = False
    is_default: bool = False


class ConsolidationScopePatch(BaseModel):
    name: str | None = None
    description: str | None = None
    country_id: uuid.UUID | None = None
    organization_id: uuid.UUID | None = None
    branch_id: uuid.UUID | None = None
    department_id: uuid.UUID | None = None
    scope_level: str | None = None
    include_child_scopes: bool | None = None
    allowed_modules: list[str] | None = None
    max_classification_allowed: str | None = None
    can_view_raw_restricted: bool | None = None
    can_use_ai_summary: bool | None = None
    can_export: bool | None = None
    is_default: bool | None = None
    is_active: bool | None = None


@router.get("/scopes")
def list_consolidation_scopes(
    user_id: uuid.UUID | None = None,
    db: Session = Depends(get_configured_db),
    current: CoreUser = Depends(require_permission("consolidation.view")),
):
    target = user_id or current.id
    if target != current.id and not _can_manage(db, current):
        raise SolaceHTTPException(403, "Cannot view another user's consolidation scopes", code="FORBIDDEN")
    if target == current.id:
        return css.list_available_for_user(db, current)
    rows = css.list_scopes_for_user(db, target)
    return [css.scope_to_dict(r) for r in rows]


@router.post("/scopes")
def create_consolidation_scope(
    body: ConsolidationScopeIn,
    db: Session = Depends(get_configured_db),
    admin: CoreUser = Depends(require_permission("consolidation.manage")),
):
    row = css.create_scope(db, actor_id=admin.id, **body.model_dump())
    db.commit()
    return row


@router.patch("/scopes/{scope_id}")
def update_consolidation_scope(
    scope_id: uuid.UUID,
    body: ConsolidationScopePatch,
    db: Session = Depends(get_configured_db),
    admin: CoreUser = Depends(require_permission("consolidation.manage")),
):
    scope = db.get(CoreConsolidationScope, scope_id)
    if scope is None:
        raise SolaceHTTPException(404, "Consolidation scope not found", code="NOT_FOUND")
    row = css.update_scope(
        db,
        scope,
        actor_id=admin.id,
        **body.model_dump(exclude_unset=True),
    )
    db.commit()
    return row


def _can_manage(db: Session, user: CoreUser) -> bool:
    from app.core.permissions import user_has_permission

    return user_has_permission(db, user, "consolidation.manage")
