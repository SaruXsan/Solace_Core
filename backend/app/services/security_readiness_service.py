"""Security readiness report for staging / production prep."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.permissions import get_user_permission_codes
from app.models.audit import AuditLoginEvent, AuditTrail
from app.models.platform import CoreSession, CoreUser, CoreUserRole
from app.services import ldap_service, platform_settings_service, settings_service


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def get_break_glass_users(db: Session) -> list[dict]:
    """Users with is_admin but no role assignments (wildcard break-glass)."""
    admins = db.scalars(
        select(CoreUser).where(
            CoreUser.is_admin == True,  # noqa: E712
            CoreUser.deleted_at.is_(None),
        )
    ).all()
    result = []
    for user in admins:
        role_count = db.scalar(
            select(func.count()).select_from(CoreUserRole).where(
                CoreUserRole.user_id == user.id
            )
        ) or 0
        perms = get_user_permission_codes(db, user)
        if role_count == 0 and "*" in perms:
            result.append(
                {
                    "id": str(user.id),
                    "username": user.username,
                    "display_name": user.display_name,
                    "email": user.email,
                    "recommendation": "Assign system_administrator role and rely on RBAC",
                }
            )
    return result


def get_security_readiness(db: Session) -> dict:
    now = _utcnow()
    since_24h = now - timedelta(hours=24)

    admins = db.scalars(
        select(CoreUser).where(
            CoreUser.is_admin == True,  # noqa: E712
            CoreUser.deleted_at.is_(None),
        )
    ).all()
    mfa_enabled_admins = sum(1 for u in admins if u.mfa_enabled)
    privileged_no_mfa = db.scalar(
        select(func.count()).select_from(CoreUser).where(
            CoreUser.is_privileged_account == True,  # noqa: E712
            CoreUser.mfa_enabled == False,  # noqa: E712
            CoreUser.deleted_at.is_(None),
        )
    ) or 0

    locked_users = db.scalar(
        select(func.count()).select_from(CoreUser).where(
            CoreUser.locked_until.isnot(None),
            CoreUser.locked_until > now,
        )
    ) or 0

    failed_24h = db.scalar(
        select(func.count()).select_from(AuditLoginEvent).where(
            AuditLoginEvent.success == False,  # noqa: E712
            AuditLoginEvent.created_at >= since_24h,
        )
    ) or 0

    active_sessions = db.scalar(
        select(func.count()).select_from(CoreSession).where(
            CoreSession.revoked_at.is_(None),
            CoreSession.expires_at > now,
        )
    ) or 0

    revoked_recent = db.scalar(
        select(func.count()).select_from(CoreSession).where(
            CoreSession.revoked_at.isnot(None),
            CoreSession.revoked_at >= since_24h,
        )
    ) or 0

    permission_denied_24h = db.scalar(
        select(func.count()).select_from(AuditTrail).where(
            AuditTrail.event_type == "security",
            AuditTrail.action == "permission_denied",
            AuditTrail.created_at >= since_24h,
        )
    ) or 0

    ldap_row = ldap_service.get_directory_settings(db)
    ldap_enabled = bool(ldap_row and ldap_row.directory_enabled)
    plain_ldap_warning = None
    if ldap_row and ldap_row.directory_type.upper() == "LDAP" and not ldap_row.use_ssl:
        plain_ldap_warning = "Plain LDAP is enabled. Use LDAPS in production."

    mfa_settings = platform_settings_service.get_mfa_settings(db)
    smtp_configured = bool(
        mfa_settings.get("smtp_host") and mfa_settings.get("has_smtp_password")
    )

    return {
        "mfa_enabled_admins_count": mfa_enabled_admins,
        "total_admins_count": len(admins),
        "privileged_users_without_mfa": privileged_no_mfa,
        "break_glass_users": get_break_glass_users(db),
        "failed_logins_last_24h": failed_24h,
        "locked_users_count": locked_users,
        "ldap": {
            "enabled": ldap_enabled,
            "directory_type": ldap_row.directory_type if ldap_row else None,
            "plain_ldap_warning": plain_ldap_warning,
        },
        "smtp": {
            "configured": smtp_configured,
            "host": mfa_settings.get("smtp_host"),
        },
        "sessions": {
            "active_count": active_sessions,
            "revoked_last_24h": revoked_recent,
        },
        "permission_denied_last_24h": permission_denied_24h,
        "encrypted_settings_vault": {
            "reachable": settings_service.get_encrypted_setting(db, "smtp_password")
            is not None
            or smtp_configured,
            "smtp_password_stored": mfa_settings.get("has_smtp_password", False),
        },
    }
