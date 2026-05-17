"""User scope assignments API."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_configured_db, require_permission
from app.models.platform import CoreUser, CoreUserScope
from app.services import scope_service

router = APIRouter(prefix="/scopes", tags=["scopes"])


class UserScopeIn(BaseModel):
    user_id: uuid.UUID
    scope_type: str
    country_id: uuid.UUID | None = None
    organization_id: uuid.UUID | None = None
    branch_id: uuid.UUID | None = None
    department_id: uuid.UUID | None = None
    is_default: bool = False


class ScopedRoleIn(BaseModel):
    user_id: uuid.UUID
    role_id: uuid.UUID
    scope_type: str
    country_id: uuid.UUID | None = None
    organization_id: uuid.UUID | None = None
    branch_id: uuid.UUID | None = None
    department_id: uuid.UUID | None = None


@router.get("/users")
def list_user_scopes(
    user_id: uuid.UUID | None = None,
    db: Session = Depends(get_configured_db),
    _user: CoreUser = Depends(require_permission("scopes.read", "user_scopes.manage")),
):
    q = select(CoreUserScope).where(CoreUserScope.is_active == True)  # noqa: E712
    if user_id:
        q = q.where(CoreUserScope.user_id == user_id)
    rows = db.scalars(q).all()
    return [scope_service.scope_to_dict(r) for r in rows]


@router.post("/users")
def assign_user_scope(
    body: UserScopeIn,
    db: Session = Depends(get_configured_db),
    admin: CoreUser = Depends(require_permission("user_scopes.manage")),
):
    row = scope_service.assign_user_scope(db, **body.model_dump(), actor_id=admin.id)
    db.commit()
    return row


@router.post("/roles")
def assign_scoped_role(
    body: ScopedRoleIn,
    db: Session = Depends(get_configured_db),
    admin: CoreUser = Depends(require_permission("role_scopes.manage", "permissions.manage")),
):
    scope_service.assign_scoped_role(db, **body.model_dump(), actor_id=admin.id)
    db.commit()
    return {"success": True}
