"""Module registry endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_configured_db, require_permission
from app.models.platform import CoreUser
from app.schemas.modules import ModuleOut, ModuleUpdateIn
from app.services import module_service

router = APIRouter(prefix="/modules", tags=["modules"])


@router.get("", response_model=list[ModuleOut])
def list_modules(
    db: Session = Depends(get_configured_db),
    _user: CoreUser = Depends(require_permission("modules.read")),
):
    return module_service.list_modules(db)


@router.patch("/{module_id}", response_model=ModuleOut)
def update_module(
    module_id: UUID,
    body: ModuleUpdateIn,
    db: Session = Depends(get_configured_db),
    admin: CoreUser = Depends(require_permission("modules.update")),
):
    row = module_service.update_module(
        db, module_id, body.model_dump(exclude_unset=True), actor_id=admin.id
    )
    db.commit()
    return row
