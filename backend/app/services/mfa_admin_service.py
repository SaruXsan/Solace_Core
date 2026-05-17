"""Admin MFA controls — cooldown reset, challenge clear, temporary disable."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.exceptions import SolaceHTTPException
from app.models.mfa import CoreMFAChallenge
from app.models.platform import CoreUser
from app.services import audit_service


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def reset_mfa_cooldown(db: Session, user_id: uuid.UUID, admin_id: uuid.UUID) -> None:
    user = db.get(CoreUser, user_id)
    if not user:
        raise SolaceHTTPException(404, "User not found")
    challenges = db.scalars(
        select(CoreMFAChallenge).where(
            CoreMFAChallenge.user_id == user_id,
            CoreMFAChallenge.consumed_at.is_(None),
        )
    ).all()
    for ch in challenges:
        ch.last_resend_at = None
    audit_service.log_admin_action(
        db,
        admin_id,
        "mfa.reset_cooldown",
        target_type="user",
        target_id=str(user_id),
    )
    audit_service.log_audit(
        db,
        "mfa",
        "admin_reset_cooldown",
        actor_user_id=admin_id,
        resource_type="user",
        resource_id=str(user_id),
    )


def clear_pending_mfa_challenges(
    db: Session, user_id: uuid.UUID, admin_id: uuid.UUID
) -> int:
    user = db.get(CoreUser, user_id)
    if not user:
        raise SolaceHTTPException(404, "User not found")
    result = db.execute(
        delete(CoreMFAChallenge).where(
            CoreMFAChallenge.user_id == user_id,
            CoreMFAChallenge.consumed_at.is_(None),
        )
    )
    count = result.rowcount or 0
    audit_service.log_admin_action(
        db,
        admin_id,
        "mfa.clear_challenges",
        target_type="user",
        target_id=str(user_id),
        detail={"cleared": count},
    )
    return count


def temporarily_disable_mfa(
    db: Session,
    user_id: uuid.UUID,
    admin_id: uuid.UUID,
    *,
    hours: int,
    reason: str,
) -> None:
    if not reason or len(reason.strip()) < 8:
        raise SolaceHTTPException(400, "Audit reason required (min 8 characters)")
    user = db.get(CoreUser, user_id)
    if not user:
        raise SolaceHTTPException(404, "User not found")
    user.mfa_disabled_until = _utcnow() + timedelta(hours=hours)
    user.mfa_disable_reason = reason.strip()[:512]
    audit_service.log_admin_action(
        db,
        admin_id,
        "mfa.temporarily_disabled",
        target_type="user",
        target_id=str(user_id),
        detail={"hours": hours, "reason": reason.strip()[:200]},
    )


def set_privileged_mfa_required(
    db: Session, user_id: uuid.UUID, admin_id: uuid.UUID, required: bool
) -> None:
    user = db.get(CoreUser, user_id)
    if not user:
        raise SolaceHTTPException(404, "User not found")
    user.is_privileged_account = required
    if required:
        user.mfa_enabled = True
    audit_service.log_admin_action(
        db,
        admin_id,
        "mfa.privileged_requirement",
        target_type="user",
        target_id=str(user_id),
        detail={"is_privileged_account": required},
    )
