"""Roles and permissions endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_configured_db, require_permission
from app.models.platform import CoreUser
from app.schemas.roles import PermissionOut, RoleCreateIn, RoleOut, RoleUpdateIn
from app.services import role_service

router = APIRouter(prefix="/roles", tags=["roles"])


@router.get("/permissions", response_model=list[PermissionOut])
def list_permissions(
    db: Session = Depends(get_configured_db),
    _user: CoreUser = Depends(
        require_permission("permissions.manage", "roles.update")
    ),
):
    return role_service.list_permissions(db)


@router.get("", response_model=list[RoleOut])
def list_roles(
    db: Session = Depends(get_configured_db),
    user: CoreUser = Depends(require_permission("roles.read")),
):
    role_service.seed_base_roles(db, user.organization_id)
    db.commit()
    return role_service.list_roles(db, user.organization_id)


@router.post("", response_model=RoleOut)
def create_role(
    body: RoleCreateIn,
    db: Session = Depends(get_configured_db),
    admin: CoreUser = Depends(require_permission("roles.create")),
):
    row = role_service.create_role(db, body.model_dump(), admin.organization_id, admin.id)
    db.commit()
    return row


@router.patch("/{role_id}", response_model=RoleOut)
def update_role(
    role_id: UUID,
    body: RoleUpdateIn,
    db: Session = Depends(get_configured_db),
    admin: CoreUser = Depends(require_permission("roles.update")),
):
    row = role_service.update_role(db, role_id, body.model_dump(exclude_unset=True), admin.id)
    db.commit()
    return row
