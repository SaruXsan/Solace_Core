from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_configured_db, require_permission
from app.models.platform import CoreUser
from app.services import audit_service, organization_service

router = APIRouter(prefix="/organizations", tags=["organizations"])


class BranchIn(BaseModel):
    name: str
    code: str
    organization_id: UUID


class DepartmentIn(BaseModel):
    name: str
    code: str
    organization_id: UUID
    branch_id: UUID | None = None


@router.get("")
def list_orgs(
    db: Session = Depends(get_configured_db),
    _user: CoreUser = Depends(
        require_permission(
            "organizations.read",
            "branches.read",
            "departments.read",
            "users.read",
        )
    ),
):
    return organization_service.list_all(db)


@router.post("/branches")
def create_branch(
    body: BranchIn,
    db: Session = Depends(get_configured_db),
    admin: CoreUser = Depends(require_permission("branches.update")),
):
    row = organization_service.create_branch(db, body.organization_id, body.name, body.code)
    audit_service.log_admin_action(
        db, admin.id, "branch_created", target_type="branch", target_id=str(row.get("id", ""))
    )
    db.commit()
    return row


@router.post("/departments")
def create_department(
    body: DepartmentIn,
    db: Session = Depends(get_configured_db),
    admin: CoreUser = Depends(require_permission("departments.update")),
):
    row = organization_service.create_department(
        db, body.organization_id, body.name, body.code, body.branch_id
    )
    audit_service.log_admin_action(
        db, admin.id, "department_created", target_type="department", target_id=str(row.get("id", ""))
    )
    db.commit()
    return row
