"""Read-only audit log queries."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit import (
    AuditAdminAction,
    AuditConfigChange,
    AuditLLMCall,
    AuditLoginEvent,
    AuditPermissionChange,
    AuditPostureViolation,
    AuditTrail,
    SystemErrorLog,
)


def _serialize_rows(rows, fields: list[str]) -> list[dict]:
    out = []
    for r in rows:
        item = {"id": str(r.id), "created_at": r.created_at.isoformat() if r.created_at else ""}
        for f in fields:
            val = getattr(r, f, None)
            item[f] = str(val) if val is not None and "id" in f and val else val
        out.append(item)
    return out


def list_audit_trail(db: Session, limit: int = 100) -> list[dict]:
    rows = db.scalars(select(AuditTrail).order_by(AuditTrail.created_at.desc()).limit(limit)).all()
    return _serialize_rows(
        rows,
        ["event_type", "action", "actor_user_id", "organization_id", "resource_type", "ip_address"],
    )


def list_login_events(db: Session, limit: int = 100) -> list[dict]:
    rows = db.scalars(select(AuditLoginEvent).order_by(AuditLoginEvent.created_at.desc()).limit(limit)).all()
    return _serialize_rows(rows, ["username", "auth_source", "success", "failure_reason", "mfa_required"])


def list_admin_actions(db: Session, limit: int = 100) -> list[dict]:
    rows = db.scalars(select(AuditAdminAction).order_by(AuditAdminAction.created_at.desc()).limit(limit)).all()
    return _serialize_rows(rows, ["admin_user_id", "action", "target_type", "target_id"])


def list_config_changes(db: Session, limit: int = 100) -> list[dict]:
    rows = db.scalars(select(AuditConfigChange).order_by(AuditConfigChange.created_at.desc()).limit(limit)).all()
    return _serialize_rows(rows, ["changed_by", "setting_key", "change_summary"])


def list_permission_changes(db: Session, limit: int = 100) -> list[dict]:
    rows = db.scalars(
        select(AuditPermissionChange).order_by(AuditPermissionChange.created_at.desc()).limit(limit)
    ).all()
    return _serialize_rows(rows, ["changed_by", "permission_code", "granted"])


def list_llm_calls(db: Session, limit: int = 100) -> list[dict]:
    rows = db.scalars(select(AuditLLMCall).order_by(AuditLLMCall.created_at.desc()).limit(limit)).all()
    return _serialize_rows(rows, ["provider", "model", "module_code", "purpose", "classification"])


def list_posture_violations(db: Session, limit: int = 100) -> list[dict]:
    rows = db.scalars(
        select(AuditPostureViolation).order_by(AuditPostureViolation.created_at.desc()).limit(limit)
    ).all()
    return _serialize_rows(rows, ["violation_type", "severity", "trend_direction"])


def list_system_errors(db: Session, limit: int = 100) -> list[dict]:
    rows = db.scalars(select(SystemErrorLog).order_by(SystemErrorLog.created_at.desc()).limit(limit)).all()
    return _serialize_rows(rows, ["source", "message", "correlation_id"])
