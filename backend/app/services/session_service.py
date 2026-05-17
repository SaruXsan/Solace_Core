"""Active session listing and revocation."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import SolaceHTTPException
from app.models.platform import CoreSession, CoreUser
from app.services import audit_service


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def list_active_sessions(
    db: Session,
    *,
    user_id: uuid.UUID | None = None,
    username: str | None = None,
    limit: int = 200,
) -> list[dict]:
    q = (
        select(CoreSession, CoreUser.username, CoreUser.display_name)
        .join(CoreUser, CoreUser.id == CoreSession.user_id)
        .where(
            CoreSession.revoked_at.is_(None),
            CoreSession.expires_at > _utcnow(),
        )
        .order_by(CoreSession.created_at.desc())
        .limit(limit)
    )
    if user_id:
        q = q.where(CoreSession.user_id == user_id)
    if username:
        q = q.where(CoreUser.username.ilike(f"%{username}%"))
    rows = db.execute(q).all()
    return [
        {
            "id": str(sess.id),
            "user_id": str(sess.user_id),
            "username": uname,
            "display_name": dname,
            "ip_address": sess.ip_address,
            "user_agent": sess.user_agent,
            "created_at": sess.created_at.isoformat() if sess.created_at else None,
            "expires_at": sess.expires_at.isoformat(),
            "is_current": False,
        }
        for sess, uname, dname in rows
    ]


def revoke_session(db: Session, session_id: uuid.UUID, admin_id: uuid.UUID) -> None:
    sess = db.get(CoreSession, session_id)
    if not sess or sess.revoked_at:
        raise SolaceHTTPException(404, "Session not found or already revoked")
    sess.revoked_at = _utcnow()
    audit_service.log_admin_action(
        db,
        admin_id,
        "sessions.revoke",
        target_type="session",
        target_id=str(session_id),
        detail={"user_id": str(sess.user_id)},
    )


def revoke_all_sessions_for_user(
    db: Session, user_id: uuid.UUID, admin_id: uuid.UUID, *, except_jti: str | None = None
) -> int:
    sessions = db.scalars(
        select(CoreSession).where(
            CoreSession.user_id == user_id,
            CoreSession.revoked_at.is_(None),
        )
    ).all()
    count = 0
    now = _utcnow()
    for sess in sessions:
        if except_jti and sess.token_jti == except_jti:
            continue
        sess.revoked_at = now
        count += 1
    audit_service.log_admin_action(
        db,
        admin_id,
        "sessions.revoke_all",
        target_type="user",
        target_id=str(user_id),
        detail={"revoked_count": count},
    )
    return count
