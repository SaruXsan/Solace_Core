"""LDAP directory sync preview and apply."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from ldap3.core.exceptions import LDAPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import SolaceHTTPException
from app.models.platform import CoreOrganization, CoreUser
from app.services import audit_service, ldap_service


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _list_directory_users(db: Session) -> list[dict[str, Any]]:
    row = ldap_service.get_directory_settings(db)
    if not row or not row.directory_enabled or not row.host:
        raise SolaceHTTPException(400, "Directory not enabled or configured")
    user_filter = "(&(objectClass=user)(objectCategory=person))"
    try:
        conn = ldap_service._service_bind(row)
        conn.search(row.base_dn, user_filter, attributes=["*"], size_limit=500)
        users = []
        for entry in conn.entries:
            users.append(
                {
                    "username": ldap_service._username_from_entry(entry, row),
                    "email": ldap_service._entry_attr(entry, row.email_attribute),
                    "display_name": ldap_service._entry_attr(entry, row.display_name_attribute),
                    "department": ldap_service._entry_attr(entry, row.department_attribute),
                    "directory_object_id": str(entry.entry_dn),
                    "groups": ldap_service._entry_groups(entry),
                }
            )
        conn.unbind()
        return users
    except LDAPException as e:
        raise SolaceHTTPException(400, f"Directory search failed: {str(e)[:200]}")


def preview_sync(db: Session) -> dict[str, list[dict[str, Any]]]:
    directory_users = _list_directory_users(db)
    dir_by_dn = {u["directory_object_id"]: u for u in directory_users if u.get("directory_object_id")}
    dir_by_name = {u["username"]: u for u in directory_users}

    existing = db.scalars(
        select(CoreUser).where(
            CoreUser.deleted_at.is_(None),
            CoreUser.is_directory_user == True,  # noqa: E712
        )
    ).all()

    created: list[dict] = []
    updated: list[dict] = []
    unchanged: list[dict] = []
    disabled: list[dict] = []

    seen_dns: set[str] = set()
    for du in directory_users:
        dn = du.get("directory_object_id")
        if dn:
            seen_dns.add(dn)
        user = None
        if dn:
            user = db.scalar(
                select(CoreUser).where(
                    CoreUser.directory_object_id == dn,
                    CoreUser.deleted_at.is_(None),
                )
            )
        if user is None:
            user = db.scalar(
                select(CoreUser).where(
                    CoreUser.username == du["username"],
                    CoreUser.deleted_at.is_(None),
                )
            )
        preview_roles = ldap_service.preview_roles_for_groups(db, du.get("groups") or [])
        item = {
            "username": du["username"],
            "email": du.get("email"),
            "display_name": du.get("display_name"),
            "directory_object_id": dn,
            "roles": preview_roles,
        }
        if user is None:
            created.append(item)
        else:
            changed = (
                user.email != (du.get("email") or user.email)
                or user.display_name != (du.get("display_name") or user.display_name)
            )
            if changed:
                updated.append(item)
            else:
                unchanged.append(item)

    for user in existing:
        if user.is_admin:
            continue
        dn = user.directory_object_id
        if dn and dn not in seen_dns and user.username not in dir_by_name:
            disabled.append(
                {
                    "username": user.username,
                    "directory_object_id": dn,
                    "reason": "not_found_in_directory",
                }
            )

    return {
        "created": created,
        "updated": updated,
        "unchanged": unchanged,
        "disabled": disabled,
    }


def apply_sync(db: Session, actor_id: uuid.UUID) -> dict[str, Any]:
    preview = preview_sync(db)
    row = ldap_service.get_directory_settings(db)
    org = db.scalar(select(CoreOrganization).limit(1))
    if not org:
        raise SolaceHTTPException(503, "No organization configured")

    counts = {"created": 0, "updated": 0, "disabled": 0}
    now = _utcnow()
    auth_label = ldap_service._auth_source_label(row) if row else "LDAP"

    for item in preview["created"]:
        du = next(
            (u for u in _list_directory_users(db) if u["username"] == item["username"]),
            None,
        )
        if not du:
            continue
        user = CoreUser(
            organization_id=org.id,
            username=du["username"],
            email=du.get("email") or f"{du['username']}@local",
            display_name=du.get("display_name") or du["username"],
            directory_source=auth_label,
            is_directory_user=True,
            directory_object_id=du.get("directory_object_id"),
            last_directory_sync_at=now,
            is_active=True,
        )
        db.add(user)
        db.flush()
        ldap_service.apply_group_roles_to_user(db, user, du.get("groups") or [])
        counts["created"] += 1

    for item in preview["updated"]:
        user = db.scalar(
            select(CoreUser).where(
                CoreUser.username == item["username"],
                CoreUser.deleted_at.is_(None),
            )
        )
        if not user:
            continue
        if user.is_admin and row and not row.overwrite_local_on_sync:
            continue
        du = next(
            (u for u in _list_directory_users(db) if u["username"] == item["username"]),
            None,
        )
        if not du:
            continue
        if du.get("email"):
            user.email = du["email"]
        if du.get("display_name"):
            user.display_name = du["display_name"]
        user.directory_source = auth_label
        user.is_directory_user = True
        user.directory_object_id = du.get("directory_object_id")
        user.last_directory_sync_at = now
        ldap_service.apply_group_roles_to_user(db, user, du.get("groups") or [])
        counts["updated"] += 1

    for item in preview["disabled"]:
        user = db.scalar(
            select(CoreUser).where(
                CoreUser.username == item["username"],
                CoreUser.deleted_at.is_(None),
            )
        )
        if user and not user.is_admin:
            user.is_active = False
            user.last_directory_sync_at = now
            counts["disabled"] += 1

    if row:
        row.last_sync_at = now
        row.last_sync_status = "success"

    audit_service.log_admin_action(
        db,
        actor_id,
        "ldap.sync_apply",
        target_type="directory",
        detail=counts,
    )
    return {"success": True, "counts": counts, "preview": preview}
