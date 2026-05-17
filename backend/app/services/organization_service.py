"""Organization, branch, department CRUD."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import SolaceHTTPException
from app.models.platform import CoreBranch, CoreDepartment, CoreOrganization


def list_all(db: Session) -> dict:
    orgs = db.scalars(select(CoreOrganization).where(CoreOrganization.deleted_at.is_(None))).all()
    branches = db.scalars(select(CoreBranch).where(CoreBranch.deleted_at.is_(None))).all()
    departments = db.scalars(select(CoreDepartment).where(CoreDepartment.deleted_at.is_(None))).all()
    return {
        "organizations": [
            {"id": str(o.id), "name": o.name, "code": o.code, "is_active": o.is_active} for o in orgs
        ],
        "branches": [
            {
                "id": str(b.id),
                "organization_id": str(b.organization_id),
                "name": b.name,
                "code": b.code,
            }
            for b in branches
        ],
        "departments": [
            {
                "id": str(d.id),
                "organization_id": str(d.organization_id),
                "branch_id": str(d.branch_id) if d.branch_id else None,
                "name": d.name,
                "code": d.code,
            }
            for d in departments
        ],
    }


def create_branch(db: Session, organization_id: uuid.UUID, name: str, code: str) -> dict:
    b = CoreBranch(organization_id=organization_id, name=name, code=code)
    db.add(b)
    db.flush()
    return {"id": str(b.id), "name": b.name, "code": b.code}


def create_department(
    db: Session,
    organization_id: uuid.UUID,
    name: str,
    code: str,
    branch_id: uuid.UUID | None = None,
) -> dict:
    d = CoreDepartment(
        organization_id=organization_id, branch_id=branch_id, name=name, code=code
    )
    db.add(d)
    db.flush()
    return {"id": str(d.id), "name": d.name, "code": d.code}
