"""Countries / jurisdictions API."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_configured_db, require_permission
from app.models.platform import CoreUser
from app.services import country_service

router = APIRouter(prefix="/countries", tags=["countries"])


class CountryIn(BaseModel):
    name: str
    code: str
    default_language: str = "en"
    supported_languages: list[str] | str | None = None
    currency_code: str | None = None
    timezone: str | None = None
    date_format: str | None = None
    rtl_enabled: bool = False
    legal_system_notes: str | None = None
    court_structure_notes: str | None = None
    is_enabled: bool = True


class CountryPatch(BaseModel):
    name: str | None = None
    default_language: str | None = None
    supported_languages: list[str] | str | None = None
    currency_code: str | None = None
    timezone: str | None = None
    date_format: str | None = None
    rtl_enabled: bool | None = None
    legal_system_notes: str | None = None
    court_structure_notes: str | None = None
    is_enabled: bool | None = None


@router.get("")
def list_countries(
    db: Session = Depends(get_configured_db),
    _user: CoreUser = Depends(require_permission("countries.read", "companies.read")),
):
    return country_service.list_countries(db)


@router.post("")
def create_country(
    body: CountryIn,
    db: Session = Depends(get_configured_db),
    admin: CoreUser = Depends(require_permission("countries.manage")),
):
    row = country_service.create_country(db, body.model_dump(), admin.id)
    db.commit()
    return row


@router.patch("/{country_id}")
def update_country(
    country_id: uuid.UUID,
    body: CountryPatch,
    db: Session = Depends(get_configured_db),
    admin: CoreUser = Depends(require_permission("countries.manage")),
):
    row = country_service.update_country(db, country_id, body.model_dump(exclude_unset=True), admin.id)
    db.commit()
    return row


@router.delete("/{country_id}")
def deactivate_country(
    country_id: uuid.UUID,
    cascade: bool = Query(
        True,
        description="When true, disables all companies, branches, and departments in this country.",
    ),
    db: Session = Depends(get_configured_db),
    admin: CoreUser = Depends(require_permission("countries.manage")),
):
    row = country_service.deactivate_country(db, country_id, admin.id, cascade=cascade)
    db.commit()
    return row
