"""Phase 2A security operations — sessions, login attempts, MFA admin."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import bearer_scheme, client_ip, get_configured_db, get_current_user, require_permission
from app.core.exceptions import SolaceHTTPException
from app.core.security import decode_access_token
from app.models.platform import CoreUser
from app.services import (
    ldap_diagnostics_service,
    login_attempt_service,
    mfa_admin_service,
    security_readiness_service,
    session_service,
)

router = APIRouter(prefix="/security", tags=["security"])


class MfaDisableIn(BaseModel):
    hours: int = Field(default=8, ge=1, le=168)
    reason: str = Field(min_length=8)


class UnlockUserIn(BaseModel):
    user_id: uuid.UUID


def _current_jti(creds=Depends(bearer_scheme)) -> str | None:
    if creds and creds.credentials:
        try:
            return decode_access_token(creds.credentials).get("jti")
        except ValueError:
            return None
    return None


@router.get("/readiness")
def security_readiness(
    db: Session = Depends(get_configured_db),
    _user: CoreUser = Depends(require_permission("security.readiness")),
):
    return security_readiness_service.get_security_readiness(db)


@router.get("/break-glass-users")
def break_glass_users(
    db: Session = Depends(get_configured_db),
    _user: CoreUser = Depends(require_permission("security.readiness")),
):
    return security_readiness_service.get_break_glass_users(db)


@router.post("/ldap/diagnostics")
def ldap_diagnostics(
    body: dict | None = None,
    db: Session = Depends(get_configured_db),
    admin: CoreUser = Depends(require_permission("ldap.test")),
):
    body = body or {}
    result = ldap_diagnostics_service.run_diagnostics(
        db,
        test_username=body.get("test_username"),
        actor_id=admin.id,
    )
    db.commit()
    return result


@router.get("/sessions")
def list_sessions(
    user_id: uuid.UUID | None = None,
    username: str | None = None,
    db: Session = Depends(get_configured_db),
    _user: CoreUser = Depends(require_permission("sessions.read")),
    current_jti: str | None = Depends(_current_jti),
):
    return session_service.list_active_sessions(
        db, user_id=user_id, username=username, current_jti=current_jti
    )


@router.post("/sessions/{session_id}/revoke")
def revoke_session(
    session_id: uuid.UUID,
    db: Session = Depends(get_configured_db),
    admin: CoreUser = Depends(require_permission("sessions.revoke")),
):
    session_service.revoke_session(db, session_id, admin.id)
    db.commit()
    return {"success": True}


@router.post("/sessions/revoke-all/{user_id}")
def revoke_all_sessions(
    user_id: uuid.UUID,
    db: Session = Depends(get_configured_db),
    admin: CoreUser = Depends(require_permission("sessions.revoke")),
):
    count = session_service.revoke_all_sessions_for_user(db, user_id, admin.id)
    db.commit()
    return {"success": True, "revoked": count}


@router.post("/sessions/revoke-current")
def revoke_current_session(
    db: Session = Depends(get_configured_db),
    user: CoreUser = Depends(require_permission("sessions.revoke")),
    jti: str | None = Depends(_current_jti),
):
    if not jti:
        raise SolaceHTTPException(400, "No session token", code="NO_SESSION")
    session_service.revoke_current_session(db, jti, user.id)
    db.commit()
    return {"success": True}


@router.post("/sessions/revoke-others")
def revoke_other_sessions(
    db: Session = Depends(get_configured_db),
    user: CoreUser = Depends(require_permission("sessions.revoke")),
    jti: str | None = Depends(_current_jti),
):
    if not jti:
        raise SolaceHTTPException(400, "No session token", code="NO_SESSION")
    count = session_service.revoke_other_sessions(db, user.id, user.id, jti)
    db.commit()
    return {"success": True, "revoked": count}


@router.get("/login-attempts")
def list_login_attempts(
    username: str | None = None,
    success: bool | None = None,
    auth_source: str | None = None,
    ip_address: str | None = None,
    db: Session = Depends(get_configured_db),
    _user: CoreUser = Depends(require_permission("login_attempts.read")),
):
    return login_attempt_service.list_login_attempts(
        db,
        username=username,
        success=success,
        auth_source=auth_source,
        ip_address=ip_address,
    )


@router.get("/login-attempts/trends")
def login_trends(
    hours: int = Query(default=24, ge=1, le=168),
    db: Session = Depends(get_configured_db),
    _user: CoreUser = Depends(require_permission("login_attempts.read")),
):
    return login_attempt_service.failed_login_trends(db, hours=hours)


@router.post("/users/unlock")
def unlock_user(
    body: UnlockUserIn,
    db: Session = Depends(get_configured_db),
    admin: CoreUser = Depends(require_permission("users.unlock")),
):
    login_attempt_service.unlock_user(db, body.user_id, admin.id)
    db.commit()
    return {"success": True}


@router.post("/users/{user_id}/mfa/reset-cooldown")
def mfa_reset_cooldown(
    user_id: uuid.UUID,
    db: Session = Depends(get_configured_db),
    admin: CoreUser = Depends(require_permission("mfa.manage")),
):
    mfa_admin_service.reset_mfa_cooldown(db, user_id, admin.id)
    db.commit()
    return {"success": True}


@router.post("/users/{user_id}/mfa/clear-challenges")
def mfa_clear_challenges(
    user_id: uuid.UUID,
    db: Session = Depends(get_configured_db),
    admin: CoreUser = Depends(require_permission("mfa.manage")),
):
    count = mfa_admin_service.clear_pending_mfa_challenges(db, user_id, admin.id)
    db.commit()
    return {"success": True, "cleared": count}


@router.post("/users/{user_id}/mfa/temporary-disable")
def mfa_temp_disable(
    user_id: uuid.UUID,
    body: MfaDisableIn,
    db: Session = Depends(get_configured_db),
    admin: CoreUser = Depends(require_permission("mfa.manage")),
):
    mfa_admin_service.temporarily_disable_mfa(
        db, user_id, admin.id, hours=body.hours, reason=body.reason
    )
    db.commit()
    return {"success": True}


@router.post("/users/{user_id}/mfa/require-privileged")
def mfa_require_privileged(
    user_id: uuid.UUID,
    required: bool = True,
    db: Session = Depends(get_configured_db),
    admin: CoreUser = Depends(require_permission("mfa.manage")),
):
    mfa_admin_service.set_privileged_mfa_required(db, user_id, admin.id, required)
    db.commit()
    return {"success": True}
