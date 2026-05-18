"""User CRUD."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import SolaceHTTPException
from app.core.security import hash_password, validate_password_strength
from app.models.platform import CoreRole, CoreUser, CoreUserRole
from app.services import audit_service


def _user_to_dict(user: CoreUser, role_ids: list[uuid.UUID]) -> dict[str, Any]:
    return {
        "id": str(user.id),
        "username": user.username,
        "email": user.email,
        "display_name": user.display_name,
        "is_active": user.is_active,
        "is_admin": user.is_admin,
        "is_service_account": user.is_service_account,
        "is_privileged_account": user.is_privileged_account,
        "mfa_enabled": user.mfa_enabled,
        "mfa_method": user.mfa_method,
        "directory_source": user.directory_source,
        "is_directory_user": user.is_directory_user,
        "organization_id": str(user.organization_id),
        "branch_id": str(user.branch_id) if user.branch_id else None,
        "department_id": str(user.department_id) if user.department_id else None,
        "role_ids": [str(r) for r in role_ids],
    }


def list_users(
    db: Session,
    organization_id: uuid.UUID | None = None,
    *,
    actor_user_id: uuid.UUID | None = None,
) -> list[dict]:
    from app.core.scope_context import require_active_organization_id
    from app.core.tenant_context import is_system_bypass
    from app.models.platform import CoreOrganization
    from app.services.organization_service import _company_list_filters

    q = select(CoreUser).where(CoreUser.deleted_at.is_(None))
    actor = db.get(CoreUser, actor_user_id) if actor_user_id else None
    platform_admin = bool(actor and actor.is_admin)

    if organization_id:
        q = q.where(CoreUser.organization_id == organization_id)
    elif not platform_admin:
        org_filter, country_filter = _company_list_filters(db, actor_user_id)
        if org_filter:
            q = q.where(CoreUser.organization_id == org_filter)
        elif country_filter:
            q = q.where(
                CoreUser.organization_id.in_(
                    select(CoreOrganization.id).where(
                        CoreOrganization.country_id == country_filter,
                        CoreOrganization.deleted_at.is_(None),
                    )
                )
            )
        elif not is_system_bypass():
            q = q.where(CoreUser.organization_id == require_active_organization_id())
    users = db.scalars(q.order_by(CoreUser.username)).all()
    out = []
    for u in users:
        roles = db.scalars(
            select(CoreUserRole.role_id).where(CoreUserRole.user_id == u.id)
        ).all()
        out.append(_user_to_dict(u, list(roles)))
    return out


def get_user(db: Session, user_id: uuid.UUID) -> dict:
    user = db.get(CoreUser, user_id)
    if not user or user.deleted_at:
        raise SolaceHTTPException(404, "User not found")
    roles = db.scalars(
        select(CoreUserRole.role_id).where(CoreUserRole.user_id == user.id)
    ).all()
    return _user_to_dict(user, list(roles))


def create_user(db: Session, data: dict, actor_id: uuid.UUID) -> dict:
    existing = db.scalar(select(CoreUser).where(CoreUser.username == data["username"]))
    if existing:
        raise SolaceHTTPException(400, "Username already exists", code="DUPLICATE")
    org_id = data.get("organization_id")
    if not org_id:
        from app.models.platform import CoreOrganization

        org = db.scalar(select(CoreOrganization).limit(1))
        if not org:
            raise SolaceHTTPException(400, "No organization exists")
        org_id = org.id

    password_hash = None
    if data.get("password"):
        errs = validate_password_strength(data["password"])
        if errs:
            raise SolaceHTTPException(400, "; ".join(errs))
        password_hash = hash_password(data["password"])
    elif not data.get("is_directory_user"):
        raise SolaceHTTPException(400, "Password required for local users")

    user = CoreUser(
        organization_id=org_id,
        branch_id=data.get("branch_id"),
        department_id=data.get("department_id"),
        email=data["email"],
        username=data["username"],
        password_hash=password_hash,
        display_name=data["display_name"],
        is_admin=data.get("is_admin", False),
        is_service_account=data.get("is_service_account", False),
        is_privileged_account=data.get("is_privileged_account", False),
        mfa_enabled=data.get("mfa_enabled", False),
        mfa_method="email_otp" if data.get("mfa_enabled") else None,
        directory_source=data.get("directory_source", "local"),
        is_directory_user=data.get("is_directory_user", False),
    )
    db.add(user)
    db.flush()
    _set_user_roles(db, user.id, data.get("role_ids", []))
    audit_service.log_admin_action(
        db, actor_id, "user_created", target_type="user", target_id=str(user.id)
    )
    return get_user(db, user.id)


def update_user(db: Session, user_id: uuid.UUID, data: dict, actor_id: uuid.UUID) -> dict:
    user = db.get(CoreUser, user_id)
    if not user or user.deleted_at:
        raise SolaceHTTPException(404, "User not found")
    for key in (
        "email",
        "display_name",
        "branch_id",
        "department_id",
        "is_active",
        "is_admin",
        "is_service_account",
        "is_privileged_account",
    ):
        if key in data and data[key] is not None:
            setattr(user, key, data[key])
    if "mfa_enabled" in data and data["mfa_enabled"] is not None:
        user.mfa_enabled = data["mfa_enabled"]
        user.mfa_method = "email_otp" if data["mfa_enabled"] else None
    if data.get("password"):
        errs = validate_password_strength(data["password"])
        if errs:
            raise SolaceHTTPException(400, "; ".join(errs))
        user.password_hash = hash_password(data["password"])
    if data.get("role_ids") is not None:
        _set_user_roles(db, user.id, data["role_ids"])
    action = "user_updated"
    if "is_active" in data and data["is_active"] is False:
        action = "user_disabled"
    audit_service.log_admin_action(
        db, actor_id, action, target_type="user", target_id=str(user.id)
    )
    return get_user(db, user.id)


def _set_user_roles(db: Session, user_id: uuid.UUID, role_ids: list) -> None:
    existing = db.scalars(select(CoreUserRole).where(CoreUserRole.user_id == user_id)).all()
    for row in existing:
        db.delete(row)
    for rid in role_ids:
        db.add(CoreUserRole(user_id=user_id, role_id=uuid.UUID(str(rid)) if not isinstance(rid, uuid.UUID) else rid))


def list_org_structure(db: Session) -> dict:
    from app.core.scope_context import require_active_organization_id
    from app.core.tenant_context import is_system_bypass
    from app.models.platform import CoreBranch, CoreDepartment, CoreOrganization

    org_filter = None if is_system_bypass() else require_active_organization_id()
    org_q = select(CoreOrganization).where(CoreOrganization.deleted_at.is_(None))
    if org_filter:
        org_q = org_q.where(CoreOrganization.id == org_filter)
    orgs = db.scalars(org_q).all()
    branch_q = select(CoreBranch).where(CoreBranch.deleted_at.is_(None))
    dept_q = select(CoreDepartment).where(CoreDepartment.deleted_at.is_(None))
    role_q = select(CoreRole).where(CoreRole.deleted_at.is_(None))
    if org_filter:
        branch_q = branch_q.where(CoreBranch.organization_id == org_filter)
        dept_q = dept_q.where(CoreDepartment.organization_id == org_filter)
        role_q = role_q.where(CoreRole.organization_id == org_filter)
    branches = db.scalars(branch_q).all()
    departments = db.scalars(dept_q).all()
    roles = db.scalars(role_q).all()
    return {
        "organizations": [{"id": str(o.id), "name": o.name, "code": o.code} for o in orgs],
        "branches": [
            {"id": str(b.id), "name": b.name, "code": b.code, "organization_id": str(b.organization_id)}
            for b in branches
        ],
        "departments": [
            {
                "id": str(d.id),
                "name": d.name,
                "code": d.code,
                "organization_id": str(d.organization_id),
                "branch_id": str(d.branch_id) if d.branch_id else None,
            }
            for d in departments
        ],
        "roles": [{"id": str(r.id), "name": r.name, "code": r.code} for r in roles],
    }
