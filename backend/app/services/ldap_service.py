"""LDAP / LDAPS directory integration."""

from __future__ import annotations

import json
import logging
from typing import Any
from uuid import UUID

from ldap3 import ALL, Connection, Server, Tls
from ldap3.core.exceptions import LDAPException
from sqlalchemy import select
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
            "email": str(getattr(entry, row.email_attribute, "")) or f"{username}@local",
            "display_name": str(getattr(entry, row.display_name_attribute, "")) or username,
            "auth_source": _auth_source_label(row),
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
    password = ""
    if row.encrypted_bind_password:
        password = decrypt_value(row.encrypted_bind_password, row.password_key_id)
    search_filter = (row.user_search_filter or "(uid={username})").format(username=username)
    try:
        server = _build_server(row)
        conn = Connection(
            server,
            user=row.bind_dn or row.bind_username,
            password=password,
            auto_bind=True,
        )
        conn.search(row.base_dn, search_filter, attributes=["*"], size_limit=1)
        if not conn.entries:
            return {"found": False, "username": username}
        entry = conn.entries[0]
        conn.unbind()
        if actor_id:
            audit_service.log_audit(db, "ldap", "test_user_lookup", actor_user_id=actor_id)
        return {
            "found": True,
            "username": username,
            "email": str(getattr(entry, row.email_attribute, "")) or None,
            "display_name": str(getattr(entry, row.display_name_attribute, "")) or None,
            "department": str(getattr(entry, row.department_attribute, "")) or None,
        }
    except LDAPException as e:
        return {"found": False, "error": str(e)[:200]}
