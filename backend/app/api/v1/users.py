"""User management endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import client_ip, get_configured_db, get_current_user, require_permission
from app.core.permissions import assert_any_permission
from app.models.platform import CoreUser
from app.schemas.users import UserCreateIn, UserOut, UserUpdateIn
from app.services import role_service, user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/structure")
def get_structure(
    db: Session = Depends(get_configured_db),
    _user: CoreUser = Depends(require_permission("users.read", "users.create", "users.update")),
):
    return user_service.list_org_structure(db)


@router.get("", response_model=list[UserOut])
def list_users(
    db: Session = Depends(get_configured_db),
    user: CoreUser = Depends(require_permission("users.read")),
):
    return user_service.list_users(db, user.organization_id)


@router.get("/{user_id}", response_model=UserOut)
def get_user(
    user_id: UUID,
    db: Session = Depends(get_configured_db),
    actor: CoreUser = Depends(require_permission("users.read")),
):
    row = user_service.get_user(db, user_id)
    if not actor.is_admin and row["organization_id"] != str(actor.organization_id):
        from app.core.exceptions import SolaceHTTPException

        raise SolaceHTTPException(403, "Cross-organization access denied", code="FORBIDDEN")
    return row


@router.post("", response_model=UserOut)
def create_user(
    body: UserCreateIn,
    db: Session = Depends(get_configured_db),
    admin: CoreUser = Depends(require_permission("users.create")),
):
    data = body.model_dump()
    if not data.get("organization_id"):
        data["organization_id"] = admin.organization_id
    row = user_service.create_user(db, data, admin.id)
    role_service.seed_base_roles(db, admin.organization_id)
    db.commit()
    return row


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: UUID,
    body: UserUpdateIn,
    request: Request,
    db: Session = Depends(get_configured_db),
    actor: CoreUser = Depends(get_current_user),
):
    payload = body.model_dump(exclude_unset=True)
    if payload.get("is_active") is False:
        assert_any_permission(
            db, actor, "users.disable", ip_address=client_ip(request)
        )
    else:
        assert_any_permission(
            db, actor, "users.update", ip_address=client_ip(request)
        )
    row = user_service.update_user(db, user_id, payload, actor.id)
    db.commit()
    return row
