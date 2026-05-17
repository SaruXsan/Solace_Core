"""LDAP / LDAPS directory integration."""

from __future__ import annotations

import json
import logging
from typing import Any
from uuid import UUID

from ldap3 import ALL, Connection, Server, Tls
from ldap3.core.exceptions import LDAPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.crypto import decrypt_value, encrypt_value, mask_secret
from app.core.exceptions import SolaceHTTPException
from app.models.auth_directory import AuthDirectorySetting
from app.models.platform import CoreUser
from app.services import audit_service

logger = logging.getLogger(__name__)


def get_directory_settings(db: Session) -> AuthDirectorySetting | None:
    return db.scalar(select(AuthDirectorySetting).limit(1))


def directory_settings_to_dict(row: AuthDirectorySetting | None) -> dict[str, Any]:
    if not row:
        return {"configured": False}
    mapping = None
    if row.role_group_mapping_json:
        try:
            mapping = json.loads(row.role_group_mapping_json)
        except json.JSONDecodeError:
            mapping = row.role_group_mapping_json
    warning = None
    if row.directory_type.upper() == "LDAP" and not row.use_ssl:
        warning = "Plain LDAP is not recommended for production. Use LDAPS."
    masked = mask_secret("********") if row.encrypted_bind_password else None
    return {
        "configured": True,
        "directory_enabled": row.directory_enabled,
        "directory_type": row.directory_type,
        "host": row.host,
        "port": row.port,
        "use_ssl": row.use_ssl,
        "use_starttls": row.use_starttls,
        "bind_dn": row.bind_dn,
        "bind_username": row.bind_username,
        "has_bind_password": bool(row.encrypted_bind_password),
        "bind_password_masked": masked,
        "base_dn": row.base_dn,
        "user_search_filter": row.user_search_filter,
        "group_search_filter": row.group_search_filter,
        "email_attribute": row.email_attribute,
        "display_name_attribute": row.display_name_attribute,
        "department_attribute": row.department_attribute,
        "role_group_mapping": mapping,
        "certificate_validation_enabled": row.certificate_validation_enabled,
        "allowed_certificate_thumbprints": row.allowed_certificate_thumbprints,
        "ca_chain_reference": row.ca_chain_reference,
        "connection_timeout_seconds": row.connection_timeout_seconds,
        "plain_ldap_warning_acknowledged": row.plain_ldap_warning_acknowledged,
        "overwrite_local_on_sync": row.overwrite_local_on_sync,
        "production_warning": warning,
    }


def save_directory_settings(
    db: Session,
    data: dict[str, Any],
    bind_password: str | None,
    changed_by: UUID | None = None,
) -> AuthDirectorySetting:
    row = get_directory_settings(db)
    if row is None:
        row = AuthDirectorySetting()
        db.add(row)
    skip = {"bind_password", "changed_by", "role_group_mapping"}
    for key, val in data.items():
        if key in skip:
            continue
        if hasattr(row, key):
            setattr(row, key, val)
    if "role_group_mapping" in data and data["role_group_mapping"] is not None:
        row.role_group_mapping_json = json.dumps(data["role_group_mapping"])
    if bind_password:
        row.encrypted_bind_password = encrypt_value(bind_password, row.password_key_id)
    db.flush()
    if changed_by:
        audit_service.log_config_change(
            db, changed_by, "Auth_DirectorySettings", "Directory settings updated"
        )
        audit_service.log_audit(
            db,
            "ldap",
            "settings_saved",
            actor_user_id=changed_by,
            resource_type="directory",
        )
    return row


def _build_server(row: AuthDirectorySetting) -> Server:
    use_ssl = row.use_ssl or row.directory_type.upper() in ("LDAPS", "ACTIVE DIRECTORY")
    tls = Tls() if use_ssl and row.certificate_validation_enabled else None
    port = row.port or (636 if use_ssl else 389)
    return Server(
        row.host,
        port=port,
        use_ssl=use_ssl,
        tls=tls,
        connect_timeout=row.connection_timeout_seconds,
    )


def _service_bind(row: AuthDirectorySetting) -> Connection:
    server = _build_server(row)
    password = ""
    if row.encrypted_bind_password:
        password = decrypt_value(row.encrypted_bind_password, row.password_key_id)
    conn = Connection(
        server,
        user=row.bind_dn or row.bind_username,
        password=password,
        auto_bind=True,
    )
    if row.use_starttls and not row.use_ssl:
        conn.start_tls()
    return conn


def _entry_attr(entry, name: str) -> str | None:
    val = getattr(entry, name, None)
    if val is None:
        return None
    if hasattr(val, "value"):
        return str(val.value) if val.value is not None else None
    return str(val) if val else None


def _entry_groups(entry) -> list[str]:
    member_of = getattr(entry, "memberOf", None)
    if member_of is None:
        return []
    if hasattr(member_of, "values"):
        return [str(v) for v in member_of.values]
    if hasattr(member_of, "value"):
        return [str(member_of.value)]
    return [str(member_of)] if member_of else []


def _username_from_entry(entry, row: AuthDirectorySetting) -> str:
    for attr in ("sAMAccountName", "uid", "cn"):
        v = _entry_attr(entry, attr)
        if v:
            return v
    dn = str(entry.entry_dn)
    return dn.split(",")[0].split("=")[-1] if "=" in dn else dn


def _auth_source_label(row: AuthDirectorySetting) -> str:
    if row.directory_type.upper() == "LDAPS" or row.use_ssl:
        return "LDAPS"
    return "LDAP"


def authenticate_directory_user(
    db: Session, username: str, password: str
) -> dict[str, Any] | None:
    """Validate credentials against directory; returns user attributes or None."""
    row = get_directory_settings(db)
    if not row or not row.directory_enabled or not row.host:
        return None
    search_filter = (row.user_search_filter or "(sAMAccountName={username})").format(
        username=username
    )
    try:
        server = _build_server(row)
        bind_password = ""
        if row.encrypted_bind_password:
            bind_password = decrypt_value(row.encrypted_bind_password, row.password_key_id)
        conn = Connection(
            server,
            user=row.bind_dn or row.bind_username,
            password=bind_password,
            auto_bind=True,
        )
        conn.search(row.base_dn, search_filter, attributes=["*"], size_limit=1)
        if not conn.entries:
            conn.unbind()
            return None
        entry = conn.entries[0]
        user_dn = str(entry.entry_dn)
        user_conn = Connection(server, user=user_dn, password=password, auto_bind=True)
        user_conn.unbind()
        conn.unbind()
        return {
            "directory_object_id": user_dn,
            "email": _entry_attr(entry, row.email_attribute) or f"{username}@local",
            "display_name": _entry_attr(entry, row.display_name_attribute) or username,
            "auth_source": _auth_source_label(row),
            "groups": _entry_groups(entry),
        }
    except LDAPException:
        logger.warning("Directory authentication failed", extra={"username": username})
        return None


def test_connection(db: Session, actor_id: UUID | None = None) -> dict[str, Any]:
    row = get_directory_settings(db)
    if not row or not row.host:
        raise SolaceHTTPException(400, "Directory settings not configured")
    warnings: list[str] = []
    if row.directory_type.upper() == "LDAP" and not row.use_ssl:
        warnings.append("Plain LDAP is not recommended for production. Use LDAPS.")
    password = ""
    if row.encrypted_bind_password:
        password = decrypt_value(row.encrypted_bind_password, row.password_key_id)
    try:
        server = _build_server(row)
        conn = Connection(
            server,
            user=row.bind_dn or row.bind_username,
            password=password,
            auto_bind=True,
        )
        conn.unbind()
        if actor_id:
            audit_service.log_audit(
                db, "ldap", "test_connection_success", actor_user_id=actor_id
            )
        return {"success": True, "message": "Connection successful", "warnings": warnings}
    except LDAPException as e:
        logger.warning("LDAP test connection failed", extra={"host": row.host})
        if actor_id:
            audit_service.log_audit(
                db, "ldap", "test_connection_failed", actor_user_id=actor_id
            )
        return {"success": False, "message": str(e)[:200], "warnings": warnings}


def test_user_lookup(
    db: Session, username: str, actor_id: UUID | None = None
) -> dict[str, Any]:
    row = get_directory_settings(db)
    if not row or not row.host:
        raise SolaceHTTPException(400, "Directory settings not configured")
    search_filter = (row.user_search_filter or "(uid={username})").format(username=username)
    try:
        conn = _service_bind(row)
        conn.search(row.base_dn, search_filter, attributes=["*"], size_limit=1)
        if not conn.entries:
            return {"found": False, "username": username}
        entry = conn.entries[0]
        conn.unbind()
        if actor_id:
            audit_service.log_audit(db, "ldap", "test_user_lookup", actor_user_id=actor_id)
        return {
            "found": True,
            "username": _username_from_entry(entry, row),
            "email": _entry_attr(entry, row.email_attribute),
            "display_name": _entry_attr(entry, row.display_name_attribute),
            "department": _entry_attr(entry, row.department_attribute),
            "directory_object_id": str(entry.entry_dn),
            "groups": _entry_groups(entry),
        }
    except LDAPException as e:
        return {"found": False, "error": str(e)[:200]}


def list_group_role_mappings(db: Session) -> list[dict[str, Any]]:
    from app.models.auth_directory import AuthGroupRoleMapping
    from app.models.platform import CoreRole

    rows = db.scalars(select(AuthGroupRoleMapping)).all()
    result = []
    for m in rows:
        role = db.get(CoreRole, m.role_id)
        result.append(
            {
                "id": str(m.id),
                "directory_group_dn": m.directory_group_dn,
                "role_id": str(m.role_id),
                "role_code": role.code if role else None,
                "role_name": role.name if role else None,
            }
        )
    return result


def save_group_role_mappings(
    db: Session, mappings: list[dict[str, Any]], actor_id: UUID | None = None
) -> list[dict[str, Any]]:
    from app.models.auth_directory import AuthGroupRoleMapping

    db.execute(delete(AuthGroupRoleMapping))
    for item in mappings:
        db.add(
            AuthGroupRoleMapping(
                directory_group_dn=item["directory_group_dn"],
                role_id=UUID(str(item["role_id"])),
            )
        )
    db.flush()
    if actor_id:
        audit_service.log_config_change(
            db, actor_id, "ldap_group_role_mapping", f"Updated {len(mappings)} mappings"
        )
        audit_service.log_audit(
            db,
            "ldap",
            "group_role_mapping_saved",
            actor_user_id=actor_id,
            detail={"count": len(mappings)},
        )
    return list_group_role_mappings(db)


def preview_roles_for_groups(db: Session, groups: list[str]) -> list[str]:
    from app.models.auth_directory import AuthGroupRoleMapping
    from app.models.platform import CoreRole

    if not groups:
        return []
    mappings = db.scalars(select(AuthGroupRoleMapping)).all()
    group_set = {g.lower() for g in groups}
    role_codes: set[str] = set()
    for m in mappings:
        if m.directory_group_dn.lower() in group_set:
            role = db.get(CoreRole, m.role_id)
            if role:
                role_codes.add(role.code)
    return sorted(role_codes)


def apply_group_roles_to_user(db: Session, user: CoreUser, groups: list[str]) -> list[str]:
    from app.models.auth_directory import AuthGroupRoleMapping
    from app.models.platform import CoreRole, CoreUserRole

    row = get_directory_settings(db)
    if user.is_admin and row and not row.overwrite_local_on_sync:
        return []
    mappings = db.scalars(select(AuthGroupRoleMapping)).all()
    group_set = {g.lower() for g in groups}
    role_ids = {
        m.role_id for m in mappings if m.directory_group_dn.lower() in group_set
    }
    if not role_ids:
        return []
    existing = db.scalars(select(CoreUserRole).where(CoreUserRole.user_id == user.id)).all()
    for ur in existing:
        db.delete(ur)
    applied: list[str] = []
    for rid in role_ids:
        db.add(CoreUserRole(user_id=user.id, role_id=rid))
        role = db.get(CoreRole, rid)
        if role:
            applied.append(role.code)
    return applied
