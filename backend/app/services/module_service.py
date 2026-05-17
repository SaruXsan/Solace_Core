"""Module registry management."""

from __future__ import annotations

import json
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import SolaceHTTPException
from app.models.platform import CoreModule
from app.services import audit_service


def list_modules(db: Session) -> list[dict]:
    rows = db.scalars(select(CoreModule).order_by(CoreModule.display_name)).all()
    return [_module_dict(m) for m in rows]


def update_module(
    db: Session, module_id: uuid.UUID, data: dict, actor_id: uuid.UUID | None = None
) -> dict:
    mod = db.get(CoreModule, module_id)
    if not mod:
        raise SolaceHTTPException(404, "Module not found")
    if mod.is_placeholder and data.get("enabled"):
        raise SolaceHTTPException(
            400,
            "Placeholder modules cannot be enabled until implemented",
            code="PLACEHOLDER_MODULE",
        )
    if data.get("enabled") is not None and data["enabled"] != mod.enabled:
        mod.enabled = data["enabled"]
        if actor_id:
            audit_service.log_admin_action(
                db,
                actor_id,
                "module_enabled" if mod.enabled else "module_disabled",
                target_type="module",
                target_id=str(mod.id),
                detail={"module_name": mod.module_name},
            )
    if data.get("description") is not None:
        mod.description = data["description"]
    return _module_dict(mod)


def _module_dict(m: CoreModule) -> dict:
    perms = []
    routes = []
    try:
        if m.permissions_json:
            perms = json.loads(m.permissions_json)
    except json.JSONDecodeError:
        pass
    try:
        if m.routes_json:
            routes = json.loads(m.routes_json)
    except json.JSONDecodeError:
        pass
    return {
        "id": str(m.id),
        "module_name": m.module_name,
        "display_name": m.display_name,
        "version": m.version,
        "description": m.description,
        "enabled": m.enabled,
        "is_placeholder": m.is_placeholder,
        "database_prefix": m.database_prefix,
        "permissions": perms if isinstance(perms, list) else [],
        "routes": routes if isinstance(routes, list) else [],
    }
