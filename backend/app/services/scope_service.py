"""User scopes, active scope resolution, and scope switching."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import SolaceHTTPException
from app.core.scope_context import ActiveScope
from app.models.platform import (
    CoreBranch,
    CoreCountry,
    CoreDepartment,
    CoreOrganization,
    CoreSession,
    CoreUser,
    CoreUserRole,
    CoreUserScope,
)
from app.services import audit_service


SCOPE_GLOBAL = "global"
SCOPE_COUNTRY = "country"
SCOPE_ORGANIZATION = "organization"
SCOPE_BRANCH = "branch"
SCOPE_DEPARTMENT = "department"


def scope_to_dict(scope: CoreUserScope) -> dict[str, Any]:
    return {
        "id": str(scope.id),
        "scope_type": scope.scope_type,
        "country_id": str(scope.country_id) if scope.country_id else None,
        "organization_id": str(scope.organization_id) if scope.organization_id else None,
        "branch_id": str(scope.branch_id) if scope.branch_id else None,
        "department_id": str(scope.department_id) if scope.department_id else None,
        "is_default": scope.is_default,
        "is_active": scope.is_active,
    }


def user_scope_to_active(scope: CoreUserScope) -> ActiveScope:
    org_id = scope.organization_id
    if scope.scope_type == SCOPE_GLOBAL and not org_id:
        org_id = None
    return ActiveScope(
        scope_type=scope.scope_type,
        country_id=scope.country_id,
        organization_id=org_id,
        branch_id=scope.branch_id,
        department_id=scope.department_id,
    )


def list_user_scopes(db: Session, user_id: uuid.UUID, *, active_only: bool = True) -> list[CoreUserScope]:
    q = select(CoreUserScope).where(CoreUserScope.user_id == user_id)
    if active_only:
        q = q.where(CoreUserScope.is_active == True)  # noqa: E712
    return list(db.scalars(q.order_by(CoreUserScope.is_default.desc())).all())


def user_has_global_scope(db: Session, user_id: uuid.UUID) -> bool:
    return (
        db.scalar(
            select(CoreUserScope.id).where(
                CoreUserScope.user_id == user_id,
                CoreUserScope.scope_type == SCOPE_GLOBAL,
                CoreUserScope.is_active == True,  # noqa: E712
            )
        )
        is not None
    )


def scope_covers_request(user_scope: CoreUserScope, requested: ActiveScope) -> bool:
    if user_scope.scope_type == SCOPE_GLOBAL:
        if requested.scope_type == SCOPE_GLOBAL:
            return True
        if requested.organization_id is None:
            return True
        return True
    if user_scope.scope_type == SCOPE_COUNTRY:
        if requested.country_id and user_scope.country_id != requested.country_id:
            return False
        return requested.scope_type in (SCOPE_COUNTRY, SCOPE_ORGANIZATION, SCOPE_BRANCH, SCOPE_DEPARTMENT)
    if user_scope.scope_type == SCOPE_ORGANIZATION:
        return (
            requested.organization_id is not None
            and user_scope.organization_id == requested.organization_id
        )
    if user_scope.scope_type == SCOPE_BRANCH:
        return (
            user_scope.organization_id == requested.organization_id
            and user_scope.branch_id == requested.branch_id
        )
    if user_scope.scope_type == SCOPE_DEPARTMENT:
        return (
            user_scope.organization_id == requested.organization_id
            and user_scope.department_id == requested.department_id
        )
    return False


def user_can_use_scope(db: Session, user_id: uuid.UUID, requested: ActiveScope) -> bool:
    if requested.scope_type == SCOPE_GLOBAL:
        return user_has_global_scope(db, user_id)
    if requested.organization_id is None and requested.scope_type != SCOPE_GLOBAL:
        return False
    scopes = list_user_scopes(db, user_id)
    return any(scope_covers_request(s, requested) for s in scopes)


def resolve_default_scope(db: Session, user: CoreUser) -> ActiveScope:
    scopes = list_user_scopes(db, user.id)
    if not scopes:
        return ActiveScope(
            scope_type=SCOPE_ORGANIZATION,
            country_id=None,
            organization_id=user.organization_id,
            branch_id=user.branch_id,
            department_id=user.department_id,
        )
    default = next((s for s in scopes if s.is_default), scopes[0])
    active = user_scope_to_active(default)
    if active.organization_id is None and user.organization_id:
        return ActiveScope(
            scope_type=default.scope_type,
            country_id=default.country_id,
            organization_id=user.organization_id,
            branch_id=default.branch_id or user.branch_id,
            department_id=default.department_id or user.department_id,
        )
    return active


def available_scopes_for_user(db: Session, user: CoreUser) -> list[dict[str, Any]]:
    if user_has_global_scope(db, user.id):
        orgs = db.scalars(
            select(CoreOrganization).where(
                CoreOrganization.deleted_at.is_(None),
                CoreOrganization.is_active == True,  # noqa: E712
            )
        ).all()
        return [
            {
                "scope_type": SCOPE_ORGANIZATION,
                "country_id": str(o.country_id) if o.country_id else None,
                "organization_id": str(o.id),
                "branch_id": None,
                "department_id": None,
                "label": o.commercial_name or o.name,
                "is_default": o.id == user.organization_id,
                "is_active": True,
            }
            for o in orgs
        ]

    scopes = list_user_scopes(db, user.id)
    if not scopes:
        org = db.get(CoreOrganization, user.organization_id)
        return [
            {
                "scope_type": SCOPE_ORGANIZATION,
                "country_id": str(org.country_id) if org and org.country_id else None,
                "organization_id": str(user.organization_id),
                "branch_id": str(user.branch_id) if user.branch_id else None,
                "department_id": str(user.department_id) if user.department_id else None,
                "label": org.name if org else "Default company",
                "is_default": True,
                "is_active": True,
            }
        ]
    out = []
    seen: set[str] = set()
    for s in scopes:
        if s.scope_type == SCOPE_GLOBAL:
            continue
        label = _scope_label(db, s)
        entry = {**scope_to_dict(s), "label": label}
        key = f"{entry['scope_type']}|{entry.get('organization_id')}"
        if key in seen:
            continue
        seen.add(key)
        out.append(entry)
    return out


def _scope_label_from_active(db: Session, active: ActiveScope) -> str:
    if active.scope_type == SCOPE_GLOBAL:
        return "Global (holding)"
    if active.organization_id:
        org = db.get(CoreOrganization, active.organization_id)
        if org:
            return org.commercial_name or org.name
    if active.country_id:
        c = db.get(CoreCountry, active.country_id)
        if c:
            return c.name
    return active.scope_type


def _scope_label(db: Session, scope: CoreUserScope) -> str:
    if scope.scope_type == SCOPE_GLOBAL:
        return "Global (holding)"
    if scope.organization_id:
        org = db.get(CoreOrganization, scope.organization_id)
        if org:
            return org.commercial_name or org.name
    if scope.country_id:
        c = db.get(CoreCountry, scope.country_id)
        if c:
            return c.name
    return scope.scope_type


def apply_session_scope(session: CoreSession, scope: ActiveScope) -> None:
    if scope.organization_id is None and scope.scope_type != SCOPE_GLOBAL:
        raise SolaceHTTPException(400, "Company scope required for tenant context")
    session.active_scope_type = scope.scope_type
    session.active_country_id = scope.country_id
    session.active_branch_id = scope.branch_id
    session.active_department_id = scope.department_id
    if scope.organization_id:
        session.organization_id = scope.organization_id


def switch_scope(
    db: Session,
    user: CoreUser,
    session: CoreSession,
    *,
    scope_type: str,
    country_id: uuid.UUID | None = None,
    organization_id: uuid.UUID | None = None,
    branch_id: uuid.UUID | None = None,
    department_id: uuid.UUID | None = None,
    ip_address: str | None = None,
) -> ActiveScope:
    requested = ActiveScope(
        scope_type=scope_type,
        country_id=country_id,
        organization_id=organization_id,
        branch_id=branch_id,
        department_id=department_id,
    )
    if user_has_global_scope(db, user.id) and organization_id:
        org = db.get(CoreOrganization, organization_id)
        if not org or org.deleted_at or not org.is_active:
            raise SolaceHTTPException(400, "Invalid or inactive company")
        requested = ActiveScope(
            scope_type=SCOPE_ORGANIZATION,
            country_id=country_id or org.country_id,
            organization_id=organization_id,
            branch_id=branch_id,
            department_id=department_id,
        )
    elif scope_type == SCOPE_GLOBAL:
        if not user_has_global_scope(db, user.id):
            raise SolaceHTTPException(403, "Global scope not permitted", code="SCOPE_FORBIDDEN")
        if organization_id is None:
            org = db.scalar(
                select(CoreOrganization).where(CoreOrganization.deleted_at.is_(None)).limit(1)
            )
            if not org:
                raise SolaceHTTPException(400, "No company configured")
            requested = ActiveScope(
                scope_type=SCOPE_ORGANIZATION,
                country_id=country_id or org.country_id,
                organization_id=org.id,
                branch_id=branch_id,
                department_id=department_id,
            )
    elif not user_can_use_scope(db, user.id, requested):
        raise SolaceHTTPException(403, "Scope not assigned to user", code="SCOPE_FORBIDDEN")

    if organization_id:
        org = db.get(CoreOrganization, organization_id)
        if not org or org.deleted_at or not org.is_active:
            raise SolaceHTTPException(400, "Invalid or inactive company")

    apply_session_scope(session, requested)
    audit_service.log_audit(
        db,
        "scope",
        "active_scope_switch",
        actor_user_id=user.id,
        organization_id=requested.organization_id,
        detail=requested.to_dict(),
        ip_address=ip_address,
    )
    return requested


def ensure_user_default_scope(
    db: Session,
    user: CoreUser,
    *,
    created_by: uuid.UUID | None = None,
) -> CoreUserScope:
    existing = db.scalar(
        select(CoreUserScope).where(CoreUserScope.user_id == user.id).limit(1)
    )
    if existing:
        return existing
    scope = CoreUserScope(
        user_id=user.id,
        scope_type=SCOPE_ORGANIZATION,
        organization_id=user.organization_id,
        branch_id=user.branch_id,
        department_id=user.department_id,
        is_default=True,
        is_active=True,
        created_by=created_by,
    )
    org = db.get(CoreOrganization, user.organization_id)
    if org and org.country_id:
        scope.country_id = org.country_id
    db.add(scope)
    db.flush()
    return scope


def ensure_admin_global_scope(db: Session, user: CoreUser) -> None:
    if not user.is_admin:
        return
    has_global = user_has_global_scope(db, user.id)
    if not has_global:
        db.add(
            CoreUserScope(
                user_id=user.id,
                scope_type=SCOPE_GLOBAL,
                is_default=True,
                is_active=True,
            )
        )
    for ur in db.scalars(select(CoreUserRole).where(CoreUserRole.user_id == user.id)).all():
        if ur.scope_type in (None, ""):
            ur.scope_type = SCOPE_GLOBAL


def assign_user_scope(
    db: Session,
    *,
    user_id: uuid.UUID,
    scope_type: str,
    actor_id: uuid.UUID,
    country_id: uuid.UUID | None = None,
    organization_id: uuid.UUID | None = None,
    branch_id: uuid.UUID | None = None,
    department_id: uuid.UUID | None = None,
    is_default: bool = False,
) -> dict:
    st = (scope_type or "").strip().lower()
    if st == SCOPE_ORGANIZATION and not organization_id:
        raise SolaceHTTPException(400, "organization_id is required for organization scope")
    if st == SCOPE_COUNTRY and not country_id:
        raise SolaceHTTPException(400, "country_id is required for country scope")
    if st == SCOPE_BRANCH and (not organization_id or not branch_id):
        raise SolaceHTTPException(400, "organization_id and branch_id are required for branch scope")
    if st == SCOPE_DEPARTMENT and (not organization_id or not department_id):
        raise SolaceHTTPException(
            400, "organization_id and department_id are required for department scope"
        )
    scope = CoreUserScope(
        user_id=user_id,
        scope_type=st or scope_type,
        country_id=country_id,
        organization_id=organization_id,
        branch_id=branch_id,
        department_id=department_id,
        is_default=is_default,
        is_active=True,
        created_by=actor_id,
    )
    db.add(scope)
    db.flush()
    audit_service.log_admin_action(
        db,
        actor_id,
        "user_scope_assigned",
        target_type="user",
        target_id=str(user_id),
        detail=scope_to_dict(scope),
    )
    return scope_to_dict(scope)


def assign_scoped_role(
    db: Session,
    *,
    user_id: uuid.UUID,
    role_id: uuid.UUID,
    scope_type: str,
    actor_id: uuid.UUID,
    country_id: uuid.UUID | None = None,
    organization_id: uuid.UUID | None = None,
    branch_id: uuid.UUID | None = None,
    department_id: uuid.UUID | None = None,
) -> None:
    db.add(
        CoreUserRole(
            user_id=user_id,
            role_id=role_id,
            scope_type=scope_type,
            country_id=country_id,
            organization_id=organization_id,
            branch_id=branch_id,
            department_id=department_id,
        )
    )
    audit_service.log_admin_action(
        db,
        actor_id,
        "role_scope_assigned",
        target_type="user",
        target_id=str(user_id),
        detail={
            "role_id": str(role_id),
            "scope_type": scope_type,
            "organization_id": str(organization_id) if organization_id else None,
        },
    )


def backfill_scopes_for_all_users(db: Session) -> None:
    users = db.scalars(select(CoreUser).where(CoreUser.deleted_at.is_(None))).all()
    for user in users:
        ensure_user_default_scope(db, user)
        ensure_admin_global_scope(db, user)
