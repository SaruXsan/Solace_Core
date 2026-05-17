"""Permission checks for RBAC."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import SolaceHTTPException
from app.models.platform import CorePermission, CoreRolePermission, CoreUser, CoreUserPermission, CoreUserRole


def get_user_permission_codes(db: Session, user: CoreUser) -> set[str]:
    """Resolve permissions from roles. is_admin grants wildcard only as break-glass when no roles assigned."""
    codes: set[str] = set()
    role_ids = db.scalars(select(CoreUserRole.role_id).where(CoreUserRole.user_id == user.id)).all()
    if role_ids:
        perm_ids = db.scalars(
            select(CoreRolePermission.permission_id).where(
                CoreRolePermission.role_id.in_(role_ids)
            )
        ).all()
        if perm_ids:
            for code in db.scalars(
                select(CorePermission.code).where(CorePermission.id.in_(perm_ids))
            ).all():
                codes.add(code)
    overrides = db.scalars(
        select(CoreUserPermission).where(CoreUserPermission.user_id == user.id)
    ).all()
    for o in overrides:
        perm = db.get(CorePermission, o.permission_id)
        if perm:
            if o.granted:
                codes.add(perm.code)
            else:
                codes.discard(perm.code)
    if not codes and user.is_admin:
        return {"*"}
    return codes


def user_has_any_permission(db: Session, user: CoreUser, *codes: str) -> bool:
    user_codes = get_user_permission_codes(db, user)
    if "*" in user_codes:
        return True
    return any(c in user_codes for c in codes)


def require_permission(db: Session, user: CoreUser, *codes: str) -> None:
    """Raise 403 if user lacks any of the required permissions."""
    if user_has_any_permission(db, user, *codes):
        return
    raise SolaceHTTPException(403, "Insufficient permissions", code="FORBIDDEN")


def assert_any_permission(
    db: Session,
    user: CoreUser,
    *codes: str,
    ip_address: str | None = None,
) -> None:
    """Check permissions; on failure log audit event and raise 403."""
    if user_has_any_permission(db, user, *codes):
        return
    from app.services import audit_service

    audit_service.log_permission_denied(
        db,
        user.id,
        list(codes),
        ip_address=ip_address,
        organization_id=user.organization_id,
    )
    try:
        db.commit()
    except Exception:
        db.rollback()
    raise SolaceHTTPException(403, "Insufficient permissions", code="FORBIDDEN")
