"""Login attempts review and account unlock."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import SolaceHTTPException
from app.models.platform import CoreLoginAttempt, CoreUser
from app.services import audit_service


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def list_login_attempts(
    db: Session,
    *,
    username: str | None = None,
    success: bool | None = None,
    auth_source: str | None = None,
    ip_address: str | None = None,
    limit: int = 500,
) -> list[dict]:
    q = select(CoreLoginAttempt).order_by(CoreLoginAttempt.created_at.desc()).limit(limit)
    if username:
        q = q.where(CoreLoginAttempt.username.ilike(f"%{username}%"))
    if success is not None:
        q = q.where(CoreLoginAttempt.success == success)
    if auth_source:
        q = q.where(CoreLoginAttempt.auth_source == auth_source)
    if ip_address:
        q = q.where(CoreLoginAttempt.ip_address.ilike(f"%{ip_address}%"))
    rows = db.scalars(q).all()
    return [
        {
            "id": str(r.id),
            "username": r.username,
            "ip_address": r.ip_address,
            "success": r.success,
            "auth_source": r.auth_source,
            "failure_reason": r.failure_reason,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


def failed_login_trends(db: Session, hours: int = 24) -> dict:
    since = _utcnow() - timedelta(hours=hours)
    rows = db.execute(
        select(
            func.datepart("hour", CoreLoginAttempt.created_at).label("hour"),
            func.count().label("cnt"),
        )
        .where(
            CoreLoginAttempt.success == False,  # noqa: E712
            CoreLoginAttempt.created_at >= since,
        )
        .group_by(func.datepart("hour", CoreLoginAttempt.created_at))
    ).all()
    return {
        "hours": hours,
        "failed_by_hour": [{"hour": int(h), "count": int(c)} for h, c in rows],
    }


def unlock_user(db: Session, user_id: uuid.UUID, admin_id: uuid.UUID) -> None:
    user = db.get(CoreUser, user_id)
    if not user:
        raise SolaceHTTPException(404, "User not found")
    user.locked_until = None
    user.failed_login_count = 0
    audit_service.log_admin_action(
        db,
        admin_id,
        "users.unlock",
        target_type="user",
        target_id=str(user_id),
    )
    audit_service.log_audit(
        db,
        "security",
        "account_unlocked",
        actor_user_id=admin_id,
        resource_type="user",
        resource_id=str(user_id),
    )
