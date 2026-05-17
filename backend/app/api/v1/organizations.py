"""Companies (Core_Organizations), branches, departments."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_configured_db, require_permission
from app.models.platform import CoreUser
from app.services import organization_service

router = APIRouter(prefix="/organizations", tags=["organizations"])


class CompanyIn(BaseModel):
    name: str
    code: str
    country_id: uuid.UUID | None = None
    legal_name: str | None = None
    commercial_name: str | None = None
    company_code: str | None = None
    registration_number: str | None = None
    tax_number: str | None = None
    default_currency: str | None = None
    default_language: str | None = None
    timezone: str | None = None
    is_active: bool = True


class BranchIn(BaseModel):
    name: str
    code: str
    organization_id: uuid.UUID | None = None
    country_id: uuid.UUID | None = None
    branch_code: str | None = None
    branch_type: str | None = None
    address: str | None = None
    city: str | None = None
    region: str | None = None
    timezone: str | None = None
    is_active: bool = True


class DepartmentIn(BaseModel):
    name: str
    code: str
    organization_id: uuid.UUID | None = None
    branch_id: uuid.UUID | None = None
    parent_department_id: uuid.UUID | None = None
    manager_user_id: uuid.UUID | None = None
    is_active: bool = True


@router.get("")
def list_orgs(
    db: Session = Depends(get_configured_db),
    _user: CoreUser = Depends(
        require_permission(
            "organizations.read",
            "companies.read",
            "branches.read",
            "departments.read",
            "users.read",
        )
    ),
):
    return organization_service.list_all(db)


@router.get("/companies")
def list_companies(
    db: Session = Depends(get_configured_db),
    _user: CoreUser = Depends(require_permission("companies.read", "organizations.read")),
):
    return organization_service.list_companies(db)


@router.post("/companies")
def create_company(
    body: CompanyIn,
    db: Session = Depends(get_configured_db),
    admin: CoreUser = Depends(require_permission("companies.manage", "organizations.update")),
):
    row = organization_service.create_company(db, body.model_dump(), admin.id)
    db.commit()
    return row


@router.patch("/companies/{company_id}")
def update_company(
    company_id: uuid.UUID,
    body: CompanyIn,
    db: Session = Depends(get_configured_db),
    admin: CoreUser = Depends(require_permission("companies.manage", "organizations.update")),
):
    row = organization_service.update_company(db, company_id, body.model_dump(exclude_unset=True), admin.id)
    db.commit()
    return row


@router.get("/branches")
def list_branches(
    organization_id: uuid.UUID | None = None,
    db: Session = Depends(get_configured_db),
    _user: CoreUser = Depends(require_permission("branches.read", "companies.read")),
):
    return organization_service.list_branches(db, organization_id)


@router.post("/branches")
def create_branch(
    body: BranchIn,
    db: Session = Depends(get_configured_db),
    admin: CoreUser = Depends(require_permission("branches.update", "companies.manage")),
):
    row = organization_service.create_branch(db, body.model_dump(), admin.id)
    db.commit()
    return row


@router.get("/departments")
def list_departments(
    organization_id: uuid.UUID | None = None,
    branch_id: uuid.UUID | None = None,
    db: Session = Depends(get_configured_db),
    _user: CoreUser = Depends(require_permission("departments.read", "companies.read")),
):
    return organization_service.list_departments(db, organization_id, branch_id)


@router.post("/departments")
def create_department(
    body: DepartmentIn,
    db: Session = Depends(get_configured_db),
    admin: CoreUser = Depends(require_permission("departments.update", "companies.manage")),
):
    row = organization_service.create_department(db, body.model_dump(), admin.id)
    db.commit()
    return row
