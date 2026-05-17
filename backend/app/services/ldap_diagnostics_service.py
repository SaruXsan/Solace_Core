"""LDAP/LDAPS staging diagnostics — safe admin-readable errors."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from ldap3.core.exceptions import LDAPException
from sqlalchemy.orm import Session

from app.core.exceptions import SolaceHTTPException
from app.services import audit_service, ldap_service

logger = logging.getLogger(__name__)


def _safe_error(exc: Exception) -> str:
    msg = str(exc).lower()
    if "certificate" in msg or "ssl" in msg or "tls" in msg:
        return "TLS/certificate validation failed. Check LDAPS settings and CA trust."
    if "invalid credentials" in msg or "bind" in msg or "49" in msg:
        return "Bind failed. Verify bind DN, username, and password."
    if "timeout" in msg or "timed out" in msg:
        return "Connection timed out. Check host, port, and firewall."
    if "no such object" in msg or "32" in msg:
        return "Base DN or search path not found."
    if "operations error" in msg:
        return "Directory operations error. Check bind permissions and base DN."
    return "Directory operation failed. See server logs for detail (secrets not logged)."


def run_diagnostics(
    db: Session,
    *,
    test_username: str | None = None,
    actor_id: UUID | None = None,
) -> dict[str, Any]:
    row = ldap_service.get_directory_settings(db)
    if not row or not row.host:
        return {
            "configured": False,
            "checks": [],
            "summary": "Directory settings not configured",
        }

    checks: list[dict[str, Any]] = []
    warnings: list[str] = []

    if row.directory_type.upper() == "LDAP" and not row.use_ssl:
        warnings.append("Plain LDAP is not recommended for production.")

    # Bind test
    bind_result = ldap_service.test_connection(db, actor_id=actor_id)
    checks.append(
        {
            "name": "service_bind",
            "success": bind_result.get("success", False),
            "message": bind_result.get("message", ""),
            "warnings": bind_result.get("warnings", []),
        }
    )

    if test_username:
        lookup = ldap_service.test_user_lookup(db, test_username, actor_id=actor_id)
        if lookup.get("found"):
            preview_roles = ldap_service.preview_roles_for_groups(
                db, lookup.get("groups") or []
            )
            checks.append(
                {
                    "name": "user_lookup",
                    "success": True,
                    "message": "User found",
                    "username": lookup.get("username"),
                    "email": lookup.get("email"),
                    "display_name": lookup.get("display_name"),
                    "department": lookup.get("department"),
                    "groups_count": len(lookup.get("groups") or []),
                    "mapped_roles": preview_roles,
                }
            )
        else:
            checks.append(
                {
                    "name": "user_lookup",
                    "success": False,
                    "message": lookup.get("error") or "User not found",
                }
            )

    if actor_id:
        audit_service.log_audit(
            db,
            "ldap",
            "diagnostics_run",
            actor_user_id=actor_id,
            detail={"checks": len(checks), "test_username": test_username},
        )

    all_ok = all(c.get("success") for c in checks if c["name"] == "service_bind")
    return {
        "configured": True,
        "directory_type": row.directory_type,
        "use_ssl": row.use_ssl,
        "use_starttls": row.use_starttls,
        "certificate_validation_enabled": row.certificate_validation_enabled,
        "checks": checks,
        "warnings": warnings,
        "summary": "All checks passed" if all_ok else "One or more checks failed",
    }


def run_scenario(
    db: Session,
    scenario: str,
    *,
    test_username: str | None = None,
    actor_id: UUID | None = None,
) -> dict[str, Any]:
    """Run a named diagnostic scenario (staging)."""
    if actor_id:
        audit_service.log_audit(
            db,
            "ldap",
            f"diagnostic_scenario_{scenario}",
            actor_user_id=actor_id,
        )
    row = ldap_service.get_directory_settings(db)
    if not row:
        raise SolaceHTTPException(400, "Directory not configured")

    if scenario == "bind_failure":
        return {
            "scenario": scenario,
            "description": "Simulate by disabling directory or using wrong bind password in settings test.",
            "hint": "Use Test Connection after entering an invalid bind password.",
        }
    if scenario == "user_not_found" and test_username:
        lookup = ldap_service.test_user_lookup(db, test_username, actor_id=actor_id)
        return {"scenario": scenario, "result": lookup}
    if scenario == "plain_ldap_warning":
        plain = row.directory_type.upper() == "LDAP" and not row.use_ssl
        return {
            "scenario": scenario,
            "plain_ldap_active": plain,
            "message": "Plain LDAP warning applies" if plain else "LDAPS/SSL in use",
        }
    return {"scenario": scenario, "message": "Unknown scenario or missing parameters"}
