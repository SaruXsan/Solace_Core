"""LDAP directory sync preview and apply."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from ldap3 import SUBTREE
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
    user_filter = ldap_service.directory_sync_search_filter(row)
    try:
        conn = ldap_service._service_bind(row)
        conn.search(
            row.base_dn,
            user_filter,
            attributes=["*"],
            size_limit=500,
            search_scope=SUBTREE,
        )
        users = []
        for entry in conn.entries:
            username = ldap_service._username_from_entry(entry, row)
            if not ldap_service.is_interactive_directory_account(entry, username):
                continue
            users.append(
                {
                    "username": username,
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


def preview_sync(db: Session) -> dict[str, Any]:
    row = ldap_service.get_directory_settings(db)
    user_filter = ldap_service.directory_sync_search_filter(row) if row else ""
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
        if ldap_service.is_non_interactive_directory_username(user.username):
            disabled.append(
                {
                    "username": user.username,
                    "directory_object_id": user.directory_object_id,
                    "reason": "computer_account",
                }
            )
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
        "directory_user_count": len(directory_users),
        "search_filter": user_filter,
        "created": created,
        "updated": updated,
        "unchanged": unchanged,
        "disabled": disabled,
    }


def _directory_import_query(organization_id: uuid.UUID | None = None):
    q = select(CoreUser).where(
        CoreUser.deleted_at.is_(None),
        CoreUser.is_directory_user == True,  # noqa: E712
        CoreUser.is_admin == False,  # noqa: E712
    )
    if organization_id:
        q = q.where(CoreUser.organization_id == organization_id)
    return q


def clear_imported_directory_users(
    db: Session, organization_id: uuid.UUID | None = None
) -> int:
    """Soft-delete all LDAP-imported users (keeps local/admin accounts)."""
    now = _utcnow()
    removed = 0
    for user in db.scalars(_directory_import_query(organization_id)).all():
        user.is_active = False
        user.deleted_at = now
        removed += 1
    return removed


def cleanup_stale_directory_users(
    db: Session,
    directory_users: list[dict[str, Any]],
    organization_id: uuid.UUID | None = None,
) -> int:
    """Remove computer accounts and directory rows no longer returned by LDAP."""
    now = _utcnow()
    valid_names = {u["username"] for u in directory_users if u.get("username")}
    removed = 0
    for user in db.scalars(_directory_import_query(organization_id)).all():
        stale = ldap_service.is_non_interactive_directory_username(user.username)
        if not stale and user.username not in valid_names:
            stale = True
        if stale:
            user.is_active = False
            user.deleted_at = now
            removed += 1
    return removed


def _resolve_sync_organization(db: Session):
    row = ldap_service.get_directory_settings(db)
    if row and row.default_sync_organization_id:
        org = db.get(CoreOrganization, row.default_sync_organization_id)
        if org and not org.deleted_at:
            return org, row
    org = db.scalar(select(CoreOrganization).where(CoreOrganization.deleted_at.is_(None)).limit(1))
    if not org:
        raise SolaceHTTPException(
            503,
            "No company configured for LDAP sync. Set default_sync_organization_id in directory settings.",
        )
    return org, row


def apply_sync(db: Session, actor_id: uuid.UUID) -> dict[str, Any]:
    org, row = _resolve_sync_organization(db)

    counts = {
        "created": 0,
        "updated": 0,
        "disabled": 0,
        "removed": 0,
        "skipped": 0,
        "errors": [],
    }
    now = _utcnow()
    auth_label = ldap_service._auth_source_label(row) if row else "LDAP"
    directory_users = _list_directory_users(db)
    counts["removed"] = cleanup_stale_directory_users(db, directory_users, org.id)
    preview = preview_sync(db)

    for item in preview["created"]:
        du = next((u for u in directory_users if u["username"] == item["username"]), None)
        if not du:
            counts["skipped"] += 1
            continue
        username = du["username"]
        if ldap_service.is_non_interactive_directory_username(username):
            counts["skipped"] += 1
            continue
        email = (du.get("email") or "").strip() or f"{username}@local"
        if db.scalar(
            select(CoreUser.id).where(
                CoreUser.deleted_at.is_(None),
                (CoreUser.username == username) | (CoreUser.email == email),
            )
        ):
            counts["skipped"] += 1
            continue
        user = CoreUser(
            organization_id=org.id,
            username=username,
            email=email,
            display_name=du.get("display_name") or username,
            directory_source=auth_label,
            is_directory_user=True,
            directory_object_id=du.get("directory_object_id"),
            last_directory_sync_at=now,
            is_active=True,
        )
        if row and row.default_sync_branch_id:
            user.branch_id = row.default_sync_branch_id
        if row and row.default_sync_department_id:
            user.department_id = row.default_sync_department_id
        try:
            with db.begin_nested():
                db.add(user)
                db.flush()
                from app.services import scope_service

                scope_service.ensure_user_default_scope(db, user, created_by=actor_id)
                ldap_service.apply_group_roles_to_user(db, user, du.get("groups") or [])
        except Exception as exc:  # noqa: BLE001
            counts["errors"].append({"username": username, "error": str(exc)[:200]})
            counts["skipped"] += 1
            continue
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
        du = next((u for u in directory_users if u["username"] == item["username"]), None)
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
            reason = item.get("reason") or "not_found_in_directory"
            if reason == "computer_account" or ldap_service.is_non_interactive_directory_username(
                user.username
            ):
                user.is_active = False
                user.deleted_at = now
                counts["removed"] += 1
            else:
                user.is_active = False
                counts["disabled"] += 1
            user.last_directory_sync_at = now

    counts["removed"] += cleanup_stale_directory_users(db, directory_users, org.id)

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
