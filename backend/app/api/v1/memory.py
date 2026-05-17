from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_configured_db, require_permission
from app.models.platform import CoreUser
from app.services import memory_service

router = APIRouter(prefix="/memory", tags=["memory"])


class AtomIn(BaseModel):
    claim: str
    domain: str = "USER_SELF"
    category: str | None = None
    data_classification: str = "INTERNAL"


@router.get("/atoms")
def list_atoms(
    user_id: UUID | None = None,
    db: Session = Depends(get_configured_db),
    user: CoreUser = Depends(require_permission("memory.read")),
):
    return memory_service.list_memory_atoms(db, user, user_id)


@router.post("/atoms")
def create_atom(
    body: AtomIn,
    db: Session = Depends(get_configured_db),
    user: CoreUser = Depends(require_permission("memory.read")),
):
    row = memory_service.create_memory_atom(db, user, body.model_dump())
    db.commit()
    return row


@router.get("/personas")
def list_personas(
    db: Session = Depends(get_configured_db),
    user: CoreUser = Depends(require_permission("personas.read")),
):
    return memory_service.list_personas(db, user)


@router.get("/rem-proposals")
def list_rem(
    db: Session = Depends(get_configured_db),
    user: CoreUser = Depends(require_permission("rem.read")),
):
    return memory_service.list_rem_proposals(db, user)
