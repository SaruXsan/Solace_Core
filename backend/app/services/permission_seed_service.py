"""Upsert foundation permissions and system roles."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.permission_codes import (
    ALL_PERMISSION_CODES,
    COMPLIANCE_REVIEWER_PERMISSIONS,
    FOUNDATION_PERMISSIONS,
    READ_ONLY_PERMISSIONS,
    SECURITY_ADMIN_PERMISSIONS,
    STANDARD_USER_PERMISSIONS,
)
from app.models.platform import (
    CoreOrganization,
    CorePermission,
    CoreRole,
    CoreRolePermission,
    CoreUser,
    CoreUserRole,
)


ROLE_TEMPLATES: list[tuple[str, str, bool, frozenset[str]]] = [
    ("system_administrator", "System Administrator", True, ALL_PERMISSION_CODES),
    ("standard_user", "Standard User", False, STANDARD_USER_PERMISSIONS),
    ("read_only", "Read Only", False, READ_ONLY_PERMISSIONS),
    ("compliance_reviewer", "Compliance Reviewer", False, COMPLIANCE_REVIEWER_PERMISSIONS),
    ("security_admin", "Security Admin", True, SECURITY_ADMIN_PERMISSIONS),
]

# Legacy role code from early foundation seed
LEGACY_ADMIN_ROLE = "admin"


def ensure_permissions(db: Session) -> dict[str, uuid.UUID]:
    """Insert missing permissions; return code -> id map."""
    code_to_id: dict[str, uuid.UUID] = {}
    for code, name, module in FOUNDATION_PERMISSIONS:
        row = db.scalar(select(CorePermission).where(CorePermission.code == code))
        if row is None:
            row = CorePermission(code=code, name=name, module_code=module)
            db.add(row)
            db.flush()
        code_to_id[code] = row.id
    db.flush()
    return code_to_id


def _sync_role_permissions(
    db: Session,
    role_id: uuid.UUID,
    perm_codes: frozenset[str],
    code_to_id: dict[str, uuid.UUID],
) -> None:
    target_ids = {code_to_id[c] for c in perm_codes if c in code_to_id}
    existing = set(
        db.scalars(
            select(CoreRolePermission.permission_id).where(
                CoreRolePermission.role_id == role_id
            )
        ).all()
    )
    for pid in existing - target_ids:
        row = db.scalar(
            select(CoreRolePermission).where(
                CoreRolePermission.role_id == role_id,
                CoreRolePermission.permission_id == pid,
            )
        )
        if row:
            db.delete(row)
    for pid in target_ids - existing:
        db.add(CoreRolePermission(role_id=role_id, permission_id=pid))


def ensure_system_roles(db: Session, organization_id: uuid.UUID) -> None:
    code_to_id = ensure_permissions(db)
    for role_code, name, requires_mfa, perm_codes in ROLE_TEMPLATES:
        role = db.scalar(
            select(CoreRole).where(
                CoreRole.organization_id == organization_id,
                CoreRole.code == role_code,
            )
        )
        if role is None:
            role = CoreRole(
                organization_id=organization_id,
                name=name,
                code=role_code,
                description=f"System role: {name}",
                requires_mfa=requires_mfa,
                is_system_role=True,
            )
            db.add(role)
            db.flush()
        _sync_role_permissions(db, role.id, perm_codes, code_to_id)

    # Upgrade legacy administrator role if present
    legacy = db.scalar(
        select(CoreRole).where(
            CoreRole.organization_id == organization_id,
            CoreRole.code == LEGACY_ADMIN_ROLE,
        )
    )
    if legacy:
        _sync_role_permissions(db, legacy.id, ALL_PERMISSION_CODES, code_to_id)


def ensure_rbac_for_all_orgs(db: Session) -> None:
    ensure_permissions(db)
    orgs = db.scalars(select(CoreOrganization).where(CoreOrganization.deleted_at.is_(None))).all()
    for org in orgs:
        ensure_system_roles(db, org.id)
    ensure_admin_users_have_system_administrator_role(db)


def ensure_admin_users_have_system_administrator_role(db: Session) -> None:
    """Assign system_administrator role to bootstrap/admin users (Phase 2A)."""
    admins = db.scalars(
        select(CoreUser).where(
            CoreUser.is_admin == True,  # noqa: E712
            CoreUser.deleted_at.is_(None),
        )
    ).all()
    for user in admins:
        role = db.scalar(
            select(CoreRole).where(
                CoreRole.organization_id == user.organization_id,
                CoreRole.code == "system_administrator",
            )
        )
        if role is None:
            continue
        exists = db.scalar(
            select(CoreUserRole.id).where(
                CoreUserRole.user_id == user.id,
                CoreUserRole.role_id == role.id,
            )
        )
        if exists is None:
            db.add(CoreUserRole(user_id=user.id, role_id=role.id))
    db.flush()
