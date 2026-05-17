"""Audit trail writers — sanitized, no secrets."""

from __future__ import annotations

import json
import logging
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.logging_config import safe_log_extra
from app.models.audit import (
    AuditAdminAction,
    AuditConfigChange,
    AuditLoginEvent,
    AuditMFAEvent,
    AuditPermissionChange,
    AuditTrail,
)

logger = logging.getLogger(__name__)


def _safe_json(data: dict[str, Any] | None) -> str | None:
    if not data:
        return None
    blocked = {"password", "otp", "token", "secret", "bind_password", "api_key"}
    clean = {k: v for k, v in data.items() if k.lower() not in blocked}
    return json.dumps(clean)


def log_audit(
    db: Session,
    event_type: str,
    action: str,
    *,
    actor_user_id: UUID | None = None,
    organization_id: UUID | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    detail: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> None:
    db.add(
        AuditTrail(
            event_type=event_type,
            action=action,
            actor_user_id=actor_user_id,
            organization_id=organization_id,
            resource_type=resource_type,
            resource_id=resource_id,
            detail_json=_safe_json(detail),
            ip_address=ip_address,
        )
    )
    logger.info(
        "audit %s %s",
        event_type,
        action,
        extra=safe_log_extra(
            actor=str(actor_user_id) if actor_user_id else None,
            resource=resource_id,
        ),
    )


def log_login(
    db: Session,
    username: str,
    auth_source: str,
    success: bool,
    *,
    user_id: UUID | None = None,
    failure_reason: str | None = None,
    mfa_required: bool = False,
    mfa_success: bool | None = None,
    ip_address: str | None = None,
) -> None:
    db.add(
        AuditLoginEvent(
            user_id=user_id,
            username=username,
            auth_source=auth_source,
            success=success,
            failure_reason=failure_reason,
            mfa_required=mfa_required,
            mfa_success=mfa_success,
            ip_address=ip_address,
        )
    )


def log_mfa_event(
    db: Session,
    user_id: UUID,
    event_type: str,
    success: bool,
    *,
    challenge_id: UUID | None = None,
    ip_address: str | None = None,
) -> None:
    db.add(
        AuditMFAEvent(
            user_id=user_id,
            event_type=event_type,
            success=success,
            challenge_id=challenge_id,
            ip_address=ip_address,
        )
    )


def log_admin_action(
    db: Session,
    admin_user_id: UUID,
    action: str,
    *,
    target_type: str | None = None,
    target_id: str | None = None,
    detail: dict[str, Any] | None = None,
) -> None:
    db.add(
        AuditAdminAction(
            admin_user_id=admin_user_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            detail_json=_safe_json(detail),
        )
    )


def log_config_change(
    db: Session,
    changed_by: UUID,
    setting_key: str,
    change_summary: str,
) -> None:
    db.add(
        AuditConfigChange(
            changed_by=changed_by,
            setting_key=setting_key,
            change_summary=change_summary,
        )
    )


def log_permission_denied(
    db: Session,
    user_id: UUID,
    required_permissions: list[str],
    *,
    ip_address: str | None = None,
    organization_id: UUID | None = None,
) -> None:
    log_audit(
        db,
        "security",
        "permission_denied",
        actor_user_id=user_id,
        organization_id=organization_id,
        detail={"required": required_permissions},
        ip_address=ip_address,
    )


def log_permission_assignment(
    db: Session,
    changed_by: UUID,
    permission_code: str,
    granted: bool,
    *,
    target_role_id: UUID | None = None,
    target_user_id: UUID | None = None,
) -> None:
    db.add(
        AuditPermissionChange(
            changed_by=changed_by,
            target_role_id=target_role_id,
            target_user_id=target_user_id,
            permission_code=permission_code,
            granted=granted,
        )
    )
    log_audit(
        db,
        "rbac",
        "permission_assignment",
        actor_user_id=changed_by,
        resource_type="role" if target_role_id else "user",
        resource_id=str(target_role_id or target_user_id),
        detail={"permission": permission_code, "granted": granted},
    )
