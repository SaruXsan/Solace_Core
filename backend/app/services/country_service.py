"""Countries / jurisdictions CRUD."""

from __future__ import annotations

import json
import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import SolaceHTTPException
from app.models.base import utcnow
from app.models.platform import CoreBranch, CoreCountry, CoreDepartment, CoreOrganization
from app.services import audit_service


def _country_dict(c: CoreCountry) -> dict[str, Any]:
    langs = c.supported_languages
    if langs and langs.startswith("["):
        try:
            langs = json.loads(langs)
        except json.JSONDecodeError:
            pass
    return {
        "id": str(c.id),
        "name": c.name,
        "code": c.code,
        "default_language": c.default_language,
        "supported_languages": langs,
        "currency_code": c.currency_code,
        "timezone": c.timezone,
        "date_format": c.date_format,
        "rtl_enabled": c.rtl_enabled,
        "legal_system_notes": c.legal_system_notes,
        "court_structure_notes": c.court_structure_notes,
        "is_enabled": c.is_enabled,
    }


def list_countries(db: Session, *, enabled_only: bool = False) -> list[dict]:
    q = select(CoreCountry).order_by(CoreCountry.name)
    if enabled_only:
        q = q.where(CoreCountry.is_enabled == True)  # noqa: E712
    return [_country_dict(c) for c in db.scalars(q).all()]


def create_country(db: Session, data: dict, actor_id: uuid.UUID) -> dict:
    existing = db.scalar(select(CoreCountry).where(CoreCountry.code == data["code"]))
    if existing:
        raise SolaceHTTPException(400, "Country code already exists")
    langs = data.get("supported_languages")
    if isinstance(langs, list):
        langs = json.dumps(langs)
    row = CoreCountry(
        name=data["name"],
        code=data["code"],
        default_language=data.get("default_language", "en"),
        supported_languages=langs,
        currency_code=data.get("currency_code"),
        timezone=data.get("timezone"),
        date_format=data.get("date_format"),
        rtl_enabled=data.get("rtl_enabled", False),
        legal_system_notes=data.get("legal_system_notes"),
        court_structure_notes=data.get("court_structure_notes"),
        is_enabled=data.get("is_enabled", True),
        created_by=actor_id,
        updated_by=actor_id,
    )
    db.add(row)
    db.flush()
    audit_service.log_audit(db, "enterprise", "country_created", actor_user_id=actor_id, detail={"code": row.code})
    return _country_dict(row)


def update_country(db: Session, country_id: uuid.UUID, data: dict, actor_id: uuid.UUID) -> dict:
    row = db.get(CoreCountry, country_id)
    if not row:
        raise SolaceHTTPException(404, "Country not found")
    for key in (
        "name",
        "default_language",
        "currency_code",
        "timezone",
        "date_format",
        "rtl_enabled",
        "legal_system_notes",
        "court_structure_notes",
        "is_enabled",
    ):
        if key in data and data[key] is not None:
            setattr(row, key, data[key])
    if "supported_languages" in data and data["supported_languages"] is not None:
        langs = data["supported_languages"]
        row.supported_languages = json.dumps(langs) if isinstance(langs, list) else langs
    row.updated_by = actor_id
    audit_service.log_audit(db, "enterprise", "country_updated", actor_user_id=actor_id, detail={"id": str(country_id)})
    return _country_dict(row)


def deactivate_country(
    db: Session,
    country_id: uuid.UUID,
    actor_id: uuid.UUID,
    *,
    cascade: bool = True,
) -> dict[str, Any]:
    """Disable a country and optionally cascade to companies, branches, and departments."""
    row = db.get(CoreCountry, country_id)
    if not row:
        raise SolaceHTTPException(404, "Country not found")

    active_orgs = db.scalar(
        select(func.count())
        .select_from(CoreOrganization)
        .where(
            CoreOrganization.country_id == country_id,
            CoreOrganization.deleted_at.is_(None),
            CoreOrganization.is_active == True,  # noqa: E712
        )
    ) or 0

    if active_orgs and not cascade:
        raise SolaceHTTPException(
            400,
            "Country has active companies. Disable with cascade to deactivate all related records.",
            code="COUNTRY_HAS_DEPENDENCIES",
        )

    now = utcnow()
    companies_disabled = 0
    branches_disabled = 0
    departments_disabled = 0

    row.is_enabled = False
    row.updated_by = actor_id

    if cascade:
        orgs = db.scalars(
            select(CoreOrganization).where(
                CoreOrganization.country_id == country_id,
                CoreOrganization.deleted_at.is_(None),
            )
        ).all()
        for org in orgs:
            if org.is_active:
                companies_disabled += 1
            org.is_active = False
            branches = db.scalars(
                select(CoreBranch).where(
                    CoreBranch.organization_id == org.id,
                    CoreBranch.deleted_at.is_(None),
                )
            ).all()
            for branch in branches:
                if branch.is_active or branch.deleted_at is None:
                    branches_disabled += 1
                branch.is_active = False
                branch.deleted_at = now
            departments = db.scalars(
                select(CoreDepartment).where(
                    CoreDepartment.organization_id == org.id,
                    CoreDepartment.deleted_at.is_(None),
                )
            ).all()
            for dept in departments:
                if dept.is_active or dept.deleted_at is None:
                    departments_disabled += 1
                dept.is_active = False
                dept.deleted_at = now

    audit_service.log_audit(
        db,
        "enterprise",
        "country_deactivated",
        actor_user_id=actor_id,
        detail={
            "country_id": str(country_id),
            "cascade": cascade,
            "companies_disabled": companies_disabled,
            "branches_disabled": branches_disabled,
            "departments_disabled": departments_disabled,
        },
    )
    return {
        **_country_dict(row),
        "cascade": cascade,
        "companies_disabled": companies_disabled,
        "branches_disabled": branches_disabled,
        "departments_disabled": departments_disabled,
    }


def seed_default_countries(db: Session) -> None:
    defaults = [
        ("Lebanon", "LB", "ar", "LBP", "Asia/Beirut", True),
        ("United Arab Emirates", "AE", "en", "AED", "Asia/Dubai", True),
        ("Kingdom of Saudi Arabia", "SA", "ar", "SAR", "Asia/Riyadh", False),
    ]
    for name, code, lang, currency, tz, enabled in defaults:
        if db.scalar(select(CoreCountry).where(CoreCountry.code == code)):
            continue
        db.add(
            CoreCountry(
                name=name,
                code=code,
                default_language=lang,
                supported_languages=json.dumps([lang, "en"]),
                currency_code=currency,
                timezone=tz,
                is_enabled=enabled,
            )
        )
