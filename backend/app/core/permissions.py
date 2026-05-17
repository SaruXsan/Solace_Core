"""Permission checks for RBAC."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import SolaceHTTPException
from app.core.scope_context import ActiveScope, get_active_scope
from app.models.platform import CorePermission, CoreRolePermission, CoreUser, CoreUserPermission, CoreUserRole
from app.services.scope_service import SCOPE_GLOBAL


def _role_applies_to_active_scope(assignment: CoreUserRole, active: ActiveScope | None) -> bool:
    st = assignment.scope_type or SCOPE_GLOBAL
    if st == SCOPE_GLOBAL:
        return True
    if active is None:
        return st == SCOPE_GLOBAL
    if st == "country":
        return active.country_id is None or assignment.country_id == active.country_id
    if st == "organization":
        return (
            active.organization_id is not None
            and assignment.organization_id == active.organization_id
        )
    if st == "branch":
        return (
            active.organization_id == assignment.organization_id
            and active.branch_id == assignment.branch_id
        )
    if st == "department":
        return (
            active.organization_id == assignment.organization_id
            and active.department_id == assignment.department_id
        )
    return False


def get_user_permission_codes(
    db: Session, user: CoreUser, active_scope: ActiveScope | None = None
) -> set[str]:
    """Resolve permissions from roles scoped to active enterprise context."""
    active = active_scope or get_active_scope()
    codes: set[str] = set()
    assignments = db.scalars(select(CoreUserRole).where(CoreUserRole.user_id == user.id)).all()
    role_ids: list[uuid.UUID] = []
    for a in assignments:
        if isinstance(a, CoreUserRole):
            if _role_applies_to_active_scope(a, active):
                role_ids.append(a.role_id)
        else:
            role_ids.append(a)  # type: ignore[arg-type]
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


def user_has_any_permission(
    db: Session, user: CoreUser, *codes: str, active_scope: ActiveScope | None = None
) -> bool:
    user_codes = get_user_permission_codes(db, user, active_scope)
    if "*" in user_codes:
        return True
    return any(c in user_codes for c in codes)


def user_has_permission(
    db: Session, user: CoreUser, code: str, active_scope: ActiveScope | None = None
) -> bool:
    return user_has_any_permission(db, user, code, active_scope=active_scope)


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
