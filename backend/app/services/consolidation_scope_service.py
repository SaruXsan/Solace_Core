"""Executive consolidation scope CRUD, session activation, and coverage resolution."""

from __future__ import annotations

import json
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.consolidation_context import ActiveConsolidationScope, set_active_consolidation_scope
from app.core.exceptions import SolaceHTTPException
from app.models.platform import (
    CoreBranch,
    CoreConsolidationScope,
    CoreCountry,
    CoreDepartment,
    CoreOrganization,
    CoreSession,
    CoreUser,
)
from app.services import audit_service

LEVEL_GLOBAL = "global"
LEVEL_COUNTRY = "country"
LEVEL_ORGANIZATION = "organization"
LEVEL_BRANCH = "branch"
LEVEL_DEPARTMENT = "department"

CLASSIFICATION_ORDER = {
    "public": 0,
    "internal": 1,
    "confidential": 2,
    "restricted": 3,
    "secret": 4,
}


def normalize_classification(value: str) -> str:
    key = (value or "Internal").strip().lower()
    mapping = {
        "public": "Public",
        "internal": "Internal",
        "confidential": "Confidential",
        "restricted": "Restricted",
        "secret": "Secret",
    }
    if key not in mapping:
        raise SolaceHTTPException(400, f"Invalid classification: {value}", code="INVALID_CLASSIFICATION")
    return mapping[key]


def classification_rank(value: str) -> int:
    return CLASSIFICATION_ORDER.get((value or "internal").strip().lower(), 1)


def _parse_modules(raw: str | None) -> list[str] | None:
    if not raw:
        return None
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return [str(x) for x in data]
    except json.JSONDecodeError:
        return [m.strip() for m in raw.split(",") if m.strip()]
    return None


def _serialize_modules(modules: list[str] | None) -> str | None:
    if not modules:
        return None
    return json.dumps(modules)


def scope_to_dict(scope: CoreConsolidationScope) -> dict[str, Any]:
    return {
        "id": str(scope.id),
        "user_id": str(scope.user_id),
        "name": scope.name,
        "description": scope.description,
        "country_id": str(scope.country_id) if scope.country_id else None,
        "organization_id": str(scope.organization_id) if scope.organization_id else None,
        "branch_id": str(scope.branch_id) if scope.branch_id else None,
        "department_id": str(scope.department_id) if scope.department_id else None,
        "scope_level": scope.scope_level,
        "include_child_scopes": scope.include_child_scopes,
        "allowed_modules": _parse_modules(scope.allowed_modules),
        "max_classification_allowed": scope.max_classification_allowed,
        "can_view_raw_restricted": scope.can_view_raw_restricted,
        "can_use_ai_summary": scope.can_use_ai_summary,
        "can_export": scope.can_export,
        "is_default": scope.is_default,
        "is_active": scope.is_active,
    }


def scope_to_active(scope: CoreConsolidationScope) -> ActiveConsolidationScope:
    return ActiveConsolidationScope(
        id=scope.id,
        user_id=scope.user_id,
        scope_level=scope.scope_level,
        country_id=scope.country_id,
        organization_id=scope.organization_id,
        branch_id=scope.branch_id,
        department_id=scope.department_id,
        include_child_scopes=scope.include_child_scopes,
        max_classification_allowed=scope.max_classification_allowed,
        can_view_raw_restricted=scope.can_view_raw_restricted,
        can_use_ai_summary=scope.can_use_ai_summary,
        can_export=scope.can_export,
        allowed_modules=_parse_modules(scope.allowed_modules),
    )


def list_scopes_for_user(
    db: Session,
    user_id: uuid.UUID,
    *,
    active_only: bool = True,
    include_inactive: bool = False,
) -> list[CoreConsolidationScope]:
    q = select(CoreConsolidationScope).where(CoreConsolidationScope.user_id == user_id)
    if active_only and not include_inactive:
        q = q.where(CoreConsolidationScope.is_active == True)  # noqa: E712
    return list(db.scalars(q.order_by(CoreConsolidationScope.is_default.desc(), CoreConsolidationScope.name)).all())


def list_available_for_user(db: Session, user: CoreUser) -> list[dict[str, Any]]:
    rows = list_scopes_for_user(db, user.id)
    return [scope_to_dict(r) for r in rows]


def get_scope_for_user(
    db: Session,
    user_id: uuid.UUID,
    scope_id: uuid.UUID,
) -> CoreConsolidationScope | None:
    return db.scalar(
        select(CoreConsolidationScope).where(
            CoreConsolidationScope.id == scope_id,
            CoreConsolidationScope.user_id == user_id,
            CoreConsolidationScope.is_active == True,  # noqa: E712
        )
    )


def create_scope(
    db: Session,
    *,
    actor_id: uuid.UUID,
    user_id: uuid.UUID,
    name: str,
    description: str | None = None,
    country_id: uuid.UUID | None = None,
    organization_id: uuid.UUID | None = None,
    branch_id: uuid.UUID | None = None,
    department_id: uuid.UUID | None = None,
    scope_level: str,
    include_child_scopes: bool = True,
    allowed_modules: list[str] | None = None,
    max_classification_allowed: str = "Internal",
    can_view_raw_restricted: bool = False,
    can_use_ai_summary: bool = False,
    can_export: bool = False,
    is_default: bool = False,
) -> dict[str, Any]:
    max_class = normalize_classification(max_classification_allowed)
    row = CoreConsolidationScope(
        user_id=user_id,
        name=name,
        description=description,
        country_id=country_id,
        organization_id=organization_id,
        branch_id=branch_id,
        department_id=department_id,
        scope_level=scope_level,
        include_child_scopes=include_child_scopes,
        allowed_modules=_serialize_modules(allowed_modules),
        max_classification_allowed=max_class,
        can_view_raw_restricted=can_view_raw_restricted,
        can_use_ai_summary=can_use_ai_summary,
        can_export=can_export,
        is_default=is_default,
        is_active=True,
        created_by=actor_id,
        updated_by=actor_id,
    )
    db.add(row)
    db.flush()
    audit_service.log_audit(
        db,
        "consolidation",
        "consolidation_scope_created",
        actor_user_id=actor_id,
        resource_type="consolidation_scope",
        resource_id=str(row.id),
        detail=scope_to_dict(row),
    )
    return scope_to_dict(row)


def update_scope(
    db: Session,
    scope: CoreConsolidationScope,
    *,
    actor_id: uuid.UUID,
    **fields: Any,
) -> dict[str, Any]:
    if "is_active" in fields and fields["is_active"] is False:
        scope.is_active = False
        audit_service.log_audit(
            db,
            "consolidation",
            "consolidation_scope_disabled",
            actor_user_id=actor_id,
            resource_type="consolidation_scope",
            resource_id=str(scope.id),
            detail=scope_to_dict(scope),
        )
    allowed = {
        "name",
        "description",
        "country_id",
        "organization_id",
        "branch_id",
        "department_id",
        "scope_level",
        "include_child_scopes",
        "allowed_modules",
        "max_classification_allowed",
        "can_view_raw_restricted",
        "can_use_ai_summary",
        "can_export",
        "is_default",
        "is_active",
    }
    for key, val in fields.items():
        if key not in allowed or val is None:
            continue
        if key == "max_classification_allowed":
            val = normalize_classification(val)
        if key == "allowed_modules":
            val = _serialize_modules(val)
        setattr(scope, key, val)
    scope.updated_by = actor_id
    db.flush()
    audit_service.log_audit(
        db,
        "consolidation",
        "consolidation_scope_updated",
        actor_user_id=actor_id,
        resource_type="consolidation_scope",
        resource_id=str(scope.id),
        detail=scope_to_dict(scope),
    )
    return scope_to_dict(scope)


def switch_consolidation_scope(
    db: Session,
    user: CoreUser,
    session: CoreSession,
    consolidation_scope_id: uuid.UUID | None,
    *,
    ip_address: str | None = None,
) -> ActiveConsolidationScope | None:
    if consolidation_scope_id is None:
        session.active_consolidation_scope_id = None
        set_active_consolidation_scope(None)
        audit_service.log_audit(
            db,
            "consolidation",
            "consolidation_scope_switched",
            actor_user_id=user.id,
            organization_id=session.organization_id,
            detail={"consolidation_scope_id": None, "cleared": True},
            ip_address=ip_address,
        )
        return None

    scope = get_scope_for_user(db, user.id, consolidation_scope_id)
    if scope is None:
        audit_service.log_audit(
            db,
            "consolidation",
            "consolidation_access_denied",
            actor_user_id=user.id,
            organization_id=session.organization_id,
            detail={
                "reason": "scope_not_assigned",
                "consolidation_scope_id": str(consolidation_scope_id),
            },
            ip_address=ip_address,
        )
        raise SolaceHTTPException(
            403,
            "Consolidation scope not assigned to user",
            code="CONSOLIDATION_FORBIDDEN",
        )

    session.active_consolidation_scope_id = scope.id
    active = scope_to_active(scope)
    set_active_consolidation_scope(active)
    audit_service.log_audit(
        db,
        "consolidation",
        "consolidation_scope_switched",
        actor_user_id=user.id,
        organization_id=session.organization_id,
        detail={"consolidation_scope_id": str(scope.id), "scope": scope_to_dict(scope)},
        ip_address=ip_address,
    )
    return active


def load_session_consolidation(db: Session, session: CoreSession) -> ActiveConsolidationScope | None:
    if not session.active_consolidation_scope_id:
        set_active_consolidation_scope(None)
        return None
    scope = db.get(CoreConsolidationScope, session.active_consolidation_scope_id)
    if scope is None or not scope.is_active:
        set_active_consolidation_scope(None)
        return None
    active = scope_to_active(scope)
    set_active_consolidation_scope(active)
    return active


def resolve_covered_entity_ids(db: Session, scope: CoreConsolidationScope) -> dict[str, set[uuid.UUID]]:
    """Resolve country/org/branch/department UUID sets covered by a consolidation scope."""
    countries: set[uuid.UUID] = set()
    organizations: set[uuid.UUID] = set()
    branches: set[uuid.UUID] = set()
    departments: set[uuid.UUID] = set()

    level = scope.scope_level
    if level == LEVEL_GLOBAL:
        countries = {c.id for c in db.scalars(select(CoreCountry)).all()}
        org_q = select(CoreOrganization).where(CoreOrganization.deleted_at.is_(None))
        organizations = {o.id for o in db.scalars(org_q).all()}
    elif level == LEVEL_COUNTRY and scope.country_id:
        countries.add(scope.country_id)
        org_q = select(CoreOrganization).where(
            CoreOrganization.country_id == scope.country_id,
            CoreOrganization.deleted_at.is_(None),
        )
        organizations = {o.id for o in db.scalars(org_q).all()}
    elif level == LEVEL_ORGANIZATION and scope.organization_id:
        organizations.add(scope.organization_id)
        org = db.get(CoreOrganization, scope.organization_id)
        if org and org.country_id:
            countries.add(org.country_id)
        if scope.include_child_scopes:
            br_q = select(CoreBranch).where(
                CoreBranch.organization_id == scope.organization_id,
                CoreBranch.deleted_at.is_(None),
            )
            branches = {b.id for b in db.scalars(br_q).all()}
            dept_q = select(CoreDepartment).where(
                CoreDepartment.organization_id == scope.organization_id,
                CoreDepartment.deleted_at.is_(None),
            )
            departments = {d.id for d in db.scalars(dept_q).all()}
    elif level == LEVEL_BRANCH and scope.branch_id:
        branches.add(scope.branch_id)
        branch = db.get(CoreBranch, scope.branch_id)
        if branch:
            organizations.add(branch.organization_id)
            if scope.include_child_scopes:
                dept_q = select(CoreDepartment).where(
                    CoreDepartment.branch_id == scope.branch_id,
                    CoreDepartment.deleted_at.is_(None),
                )
                departments = {d.id for d in db.scalars(dept_q).all()}
    elif level == LEVEL_DEPARTMENT and scope.department_id:
        departments.add(scope.department_id)
        dept = db.get(CoreDepartment, scope.department_id)
        if dept:
            organizations.add(dept.organization_id)
            if dept.branch_id:
                branches.add(dept.branch_id)

    return {
        "countries": countries,
        "organizations": organizations,
        "branches": branches,
        "departments": departments,
    }


def ensure_admin_default_consolidation(db: Session, user: CoreUser) -> None:
    """Grant bootstrap admin a global consolidation scope if none exists."""
    if not user.is_admin:
        return
    existing = db.scalar(
        select(CoreConsolidationScope.id).where(
            CoreConsolidationScope.user_id == user.id,
            CoreConsolidationScope.is_active == True,  # noqa: E712
        )
    )
    if existing:
        return
    create_scope(
        db,
        actor_id=user.id,
        user_id=user.id,
        name="Global executive consolidation",
        description="Bootstrap global consolidation scope for system administrator",
        scope_level=LEVEL_GLOBAL,
        include_child_scopes=True,
        max_classification_allowed="Confidential",
        can_view_raw_restricted=False,
        can_use_ai_summary=True,
        can_export=True,
        is_default=True,
    )
