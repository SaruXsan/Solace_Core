"""Dashboard metrics from real queries."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.audit import AuditLLMCall, AuditLoginEvent
from app.models.compliance import ComplianceEvidenceLibrary, ComplianceIncident
from app.models.platform import CoreModule, CoreUser
from app.services import bootstrap_store, platform_settings_service


def get_dashboard_stats(db: Session) -> dict:
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    total_users = db.scalar(select(func.count()).select_from(CoreUser).where(CoreUser.deleted_at.is_(None))) or 0
    active_users = db.scalar(
        select(func.count()).select_from(CoreUser).where(
            CoreUser.deleted_at.is_(None), CoreUser.is_active == True  # noqa: E712
        )
    ) or 0
    locked_users = db.scalar(
        select(func.count()).select_from(CoreUser).where(
            CoreUser.locked_until.isnot(None),
            CoreUser.locked_until > datetime.now(timezone.utc),
        )
    ) or 0
    mfa_users = db.scalar(
        select(func.count()).select_from(CoreUser).where(
            CoreUser.mfa_enabled == True, CoreUser.deleted_at.is_(None)  # noqa: E712
        )
    ) or 0
    failed_today = db.scalar(
        select(func.count()).select_from(AuditLoginEvent).where(
            AuditLoginEvent.success == False,  # noqa: E712
            AuditLoginEvent.created_at >= today_start,
        )
    ) or 0
    enabled_modules = db.scalar(
        select(func.count()).select_from(CoreModule).where(CoreModule.enabled == True)  # noqa: E712
    ) or 0
    evidence_count = db.scalar(select(func.count()).select_from(ComplianceEvidenceLibrary)) or 0
    open_incidents = db.scalar(
        select(func.count()).select_from(ComplianceIncident).where(
            ComplianceIncident.status == "open"
        )
    ) or 0
    ai_calls_today = db.scalar(
        select(func.count()).select_from(AuditLLMCall).where(AuditLLMCall.created_at >= today_start)
    ) or 0
    db_status = platform_settings_service.get_database_status()
    return {
        "total_users": total_users,
        "active_users": active_users,
        "locked_users": locked_users,
        "mfa_enabled_users": mfa_users,
        "failed_logins_today": failed_today,
        "enabled_modules": enabled_modules,
        "evidence_records": evidence_count,
        "open_incidents": open_incidents,
        "ai_calls_today": ai_calls_today,
        "system_health": {
            "database_connected": db_status.get("connected", False),
            "setup_complete": bootstrap_store.is_setup_complete(),
        },
    }
