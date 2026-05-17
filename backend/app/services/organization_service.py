"""Companies (Core_Organizations), branches, departments."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import SolaceHTTPException
from app.core.scope_context import require_active_organization_id
from app.core.tenant_context import is_system_bypass
from app.models.platform import CoreBranch, CoreDepartment, CoreOrganization
from app.services import audit_service, scope_service


def _org_dict(o: CoreOrganization) -> dict[str, Any]:
    return {
        "id": str(o.id),
        "country_id": str(o.country_id) if o.country_id else None,
        "name": o.name,
        "code": o.code,
        "legal_name": o.legal_name,
        "commercial_name": o.commercial_name,
        "company_code": o.company_code,
        "registration_number": o.registration_number,
        "tax_number": o.tax_number,
        "default_currency": o.default_currency,
        "default_language": o.default_language,
        "timezone": o.timezone,
        "is_active": o.is_active,
    }


def _branch_dict(b: CoreBranch) -> dict[str, Any]:
    return {
        "id": str(b.id),
        "organization_id": str(b.organization_id),
        "country_id": str(b.country_id) if b.country_id else None,
        "name": b.name,
        "code": b.code,
        "branch_code": b.branch_code,
        "branch_type": b.branch_type,
        "address": b.address,
        "city": b.city,
        "region": b.region,
        "timezone": b.timezone,
        "is_active": b.is_active,
    }


def _dept_dict(d: CoreDepartment) -> dict[str, Any]:
    return {
        "id": str(d.id),
        "organization_id": str(d.organization_id),
        "branch_id": str(d.branch_id) if d.branch_id else None,
        "parent_department_id": str(d.parent_department_id) if d.parent_department_id else None,
        "manager_user_id": str(d.manager_user_id) if d.manager_user_id else None,
        "name": d.name,
        "code": d.code,
        "is_active": d.is_active,
    }


def _scoped_org_filter():
    if is_system_bypass():
        return None
    return require_active_organization_id()


def list_companies(db: Session, *, country_id: uuid.UUID | None = None) -> list[dict]:
    q = select(CoreOrganization).where(CoreOrganization.deleted_at.is_(None))
    org_filter = _scoped_org_filter()
    if org_filter:
        q = q.where(CoreOrganization.id == org_filter)
    if country_id:
        q = q.where(CoreOrganization.country_id == country_id)
    return [_org_dict(o) for o in db.scalars(q.order_by(CoreOrganization.name)).all()]


def list_branches(db: Session, organization_id: uuid.UUID | None = None) -> list[dict]:
    q = select(CoreBranch).where(CoreBranch.deleted_at.is_(None))
    org_filter = _scoped_org_filter()
    if org_filter:
        q = q.where(CoreBranch.organization_id == org_filter)
    elif organization_id:
        q = q.where(CoreBranch.organization_id == organization_id)
    return [_branch_dict(b) for b in db.scalars(q.order_by(CoreBranch.name)).all()]


def list_departments(
    db: Session, organization_id: uuid.UUID | None = None, branch_id: uuid.UUID | None = None
) -> list[dict]:
    q = select(CoreDepartment).where(CoreDepartment.deleted_at.is_(None))
    org_filter = _scoped_org_filter()
    if org_filter:
        q = q.where(CoreDepartment.organization_id == org_filter)
    elif organization_id:
        q = q.where(CoreDepartment.organization_id == organization_id)
    if branch_id:
        q = q.where(CoreDepartment.branch_id == branch_id)
    return [_dept_dict(d) for d in db.scalars(q.order_by(CoreDepartment.name)).all()]


def list_all(db: Session) -> dict:
    return {
        "organizations": list_companies(db),
        "branches": list_branches(db),
        "departments": list_departments(db),
    }


def create_company(db: Session, data: dict, actor_id: uuid.UUID) -> dict:
    if db.scalar(select(CoreOrganization).where(CoreOrganization.code == data["code"])):
        raise SolaceHTTPException(400, "Company code already exists")
    o = CoreOrganization(
        country_id=data.get("country_id"),
        name=data["name"],
        code=data["code"],
        legal_name=data.get("legal_name"),
        commercial_name=data.get("commercial_name"),
        company_code=data.get("company_code"),
        registration_number=data.get("registration_number"),
        tax_number=data.get("tax_number"),
        default_currency=data.get("default_currency"),
        default_language=data.get("default_language"),
        timezone=data.get("timezone"),
        is_active=data.get("is_active", True),
    )
    db.add(o)
    db.flush()
    audit_service.log_audit(
        db, "enterprise", "company_created", actor_user_id=actor_id, detail={"code": o.code}
    )
    return _org_dict(o)


def update_company(db: Session, org_id: uuid.UUID, data: dict, actor_id: uuid.UUID) -> dict:
    o = db.get(CoreOrganization, org_id)
    if not o or o.deleted_at:
        raise SolaceHTTPException(404, "Company not found")
    for key in (
        "country_id",
        "name",
        "legal_name",
        "commercial_name",
        "company_code",
        "registration_number",
        "tax_number",
        "default_currency",
        "default_language",
        "timezone",
        "is_active",
    ):
        if key in data and data[key] is not None:
            setattr(o, key, data[key])
    audit_service.log_audit(
        db, "enterprise", "company_updated", actor_user_id=actor_id, detail={"id": str(org_id)}
    )
    return _org_dict(o)


def create_branch(db: Session, data: dict, actor_id: uuid.UUID) -> dict:
    org_id = data.get("organization_id") or _scoped_org_filter()
    if not org_id:
        raise SolaceHTTPException(400, "organization_id required")
    b = CoreBranch(
        organization_id=org_id,
        country_id=data.get("country_id"),
        name=data["name"],
        code=data["code"],
        branch_code=data.get("branch_code"),
        branch_type=data.get("branch_type"),
        address=data.get("address"),
        city=data.get("city"),
        region=data.get("region"),
        timezone=data.get("timezone"),
        is_active=data.get("is_active", True),
    )
    db.add(b)
    db.flush()
    audit_service.log_audit(db, "enterprise", "branch_created", actor_user_id=actor_id, detail={"code": b.code})
    return _branch_dict(b)


def create_department(db: Session, data: dict, actor_id: uuid.UUID) -> dict:
    org_id = data.get("organization_id") or _scoped_org_filter()
    if not org_id:
        raise SolaceHTTPException(400, "organization_id required")
    d = CoreDepartment(
        organization_id=org_id,
        branch_id=data.get("branch_id"),
        parent_department_id=data.get("parent_department_id"),
        manager_user_id=data.get("manager_user_id"),
        name=data["name"],
        code=data["code"],
        is_active=data.get("is_active", True),
    )
    db.add(d)
    db.flush()
    audit_service.log_audit(db, "enterprise", "department_created", actor_user_id=actor_id, detail={"code": d.code})
    return _dept_dict(d)


# Backward-compatible aliases
create_branch_legacy = create_branch
create_department_legacy = create_department
