"""Role and permission management."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import SolaceHTTPException
from app.models.platform import CorePermission, CoreRole, CoreRolePermission
from app.services import audit_service


def list_permissions(db: Session) -> list[dict]:
    rows = db.scalars(select(CorePermission).order_by(CorePermission.code)).all()
    return [
        {
            "id": str(p.id),
            "code": p.code,
            "name": p.name,
            "module_code": p.module_code,
        }
        for p in rows
    ]


def _role_permissions(db: Session, role_id: uuid.UUID) -> list[uuid.UUID]:
    return list(
        db.scalars(
            select(CoreRolePermission.permission_id).where(
                CoreRolePermission.role_id == role_id
            )
        ).all()
    )


def list_roles(db: Session, organization_id: uuid.UUID | None = None) -> list[dict]:
    q = select(CoreRole).where(CoreRole.deleted_at.is_(None))
    if organization_id:
        q = q.where(CoreRole.organization_id == organization_id)
    roles = db.scalars(q.order_by(CoreRole.name)).all()
    return [
        {
            "id": str(r.id),
            "name": r.name,
            "code": r.code,
            "description": r.description,
            "requires_mfa": r.requires_mfa,
            "is_system_role": r.is_system_role,
            "permission_ids": [str(p) for p in _role_permissions(db, r.id)],
        }
        for r in roles
    ]


def create_role(db: Session, data: dict, org_id: uuid.UUID, actor_id: uuid.UUID) -> dict:
    if db.scalar(select(CoreRole).where(CoreRole.code == data["code"])):
        raise SolaceHTTPException(400, "Role code already exists")
    role = CoreRole(
        organization_id=org_id,
        name=data["name"],
        code=data["code"],
        description=data.get("description"),
        requires_mfa=data.get("requires_mfa", False),
    )
    db.add(role)
    db.flush()
    _set_role_permissions(
        db, role.id, data.get("permission_ids", []), actor_id=actor_id
    )
    audit_service.log_admin_action(
        db, actor_id, "role_created", target_type="role", target_id=str(role.id)
    )
    return list_roles(db, org_id)[-1]


def update_role(
    db: Session, role_id: uuid.UUID, data: dict, actor_id: uuid.UUID
) -> dict:
    role = db.get(CoreRole, role_id)
    if not role or role.deleted_at:
        raise SolaceHTTPException(404, "Role not found")
    if role.is_system_role and data.get("permission_ids") is not None:
        pass  # allow permission updates on system roles
    for key in ("name", "description", "requires_mfa"):
        if key in data and data[key] is not None:
            setattr(role, key, data[key])
    if data.get("permission_ids") is not None:
        _set_role_permissions(db, role.id, data["permission_ids"], actor_id=actor_id)
    audit_service.log_admin_action(
        db, actor_id, "role_updated", target_type="role", target_id=str(role.id)
    )
    perms = _role_permissions(db, role.id)
    return {
        "id": str(role.id),
        "name": role.name,
        "code": role.code,
        "description": role.description,
        "requires_mfa": role.requires_mfa,
        "is_system_role": role.is_system_role,
        "permission_ids": [str(p) for p in perms],
    }


def _set_role_permissions(
    db: Session,
    role_id: uuid.UUID,
    permission_ids: list,
    *,
    actor_id: uuid.UUID | None = None,
) -> None:
    old_perm_ids = set(
        db.scalars(
            select(CoreRolePermission.permission_id).where(
                CoreRolePermission.role_id == role_id
            )
        ).all()
    )
    new_perm_ids = {
        uuid.UUID(str(pid)) if not isinstance(pid, uuid.UUID) else pid for pid in permission_ids
    }
    for row in db.scalars(
        select(CoreRolePermission).where(CoreRolePermission.role_id == role_id)
    ).all():
        db.delete(row)
    for pid in new_perm_ids:
        db.add(CoreRolePermission(role_id=role_id, permission_id=pid))
    if actor_id is not None:
        all_perm_ids = old_perm_ids | new_perm_ids
        for pid in all_perm_ids:
            perm = db.get(CorePermission, pid)
            if not perm:
                continue
            was = pid in old_perm_ids
            now = pid in new_perm_ids
            if was != now:
                audit_service.log_permission_assignment(
                    db,
                    actor_id,
                    perm.code,
                    granted=now,
                    target_role_id=role_id,
                )


def seed_base_roles(db: Session, organization_id: uuid.UUID) -> None:
    """Ensure foundation permissions and system roles exist for an organization."""
    from app.services import permission_seed_service

    permission_seed_service.ensure_system_roles(db, organization_id)
