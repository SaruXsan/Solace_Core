"""Authentication endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import bearer_scheme, client_ip, get_configured_db, get_current_user
from app.core.config import settings
from app.core.exceptions import SolaceHTTPException
from app.core.scope_context import set_active_scope
from app.core.security import create_access_token, decode_access_token
from app.core.tenant_context import set_organization_id
from app.models.platform import CoreSession
from app.models.platform import CoreUser
from app.services import auth_service, mfa_service

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str
    mfa_otp: str | None = None


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    mfa_required: bool = False
    challenge_id: str | None = None
    destination_masked: str | None = None
    expires_at: str | None = None


class MfaVerifyLoginIn(BaseModel):
    challenge_id: uuid.UUID
    otp: str = Field(min_length=6, max_length=6)


class MfaResendLoginIn(BaseModel):
    challenge_id: uuid.UUID


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    display_name: str
    is_admin: bool
    organization_id: str
    mfa_enabled: bool
    permissions: list[str] = []


class ActiveScopeOut(BaseModel):
    scope_type: str
    country_id: str | None = None
    organization_id: str | None = None
    branch_id: str | None = None
    department_id: str | None = None
    label: str | None = None


class MeResponse(UserResponse):
    setup_complete: bool = True
    active_scope: ActiveScopeOut | None = None
    available_scopes: list[ActiveScopeOut] = []


class SwitchScopeIn(BaseModel):
    scope_type: str
    country_id: uuid.UUID | None = None
    organization_id: uuid.UUID | None = None
    branch_id: uuid.UUID | None = None
    department_id: uuid.UUID | None = None


@router.post("/login", response_model=LoginResponse)
def login(
    body: LoginRequest,
    request: Request,
    db: Session = Depends(get_configured_db),
) -> LoginResponse:
    from app.services import bootstrap_store

    if not bootstrap_store.is_setup_complete():
        raise SolaceHTTPException(503, "First-run setup required", code="SETUP_REQUIRED")
    user = auth_service.authenticate_user(
        db, body.username, body.password, ip_address=client_ip(request)
    )
    if mfa_service.user_requires_mfa(db, user):
        if body.mfa_otp:
            mfa_service.verify_email_otp(db, user.id, body.mfa_otp, client_ip(request))
        else:
            challenge = mfa_service.create_email_otp_challenge(
                db, user, client_ip(request), request.headers.get("user-agent")
            )
            db.commit()
            return LoginResponse(
                access_token="",
                mfa_required=True,
                challenge_id=str(challenge.id),
                destination_masked=challenge.destination_masked,
                expires_at=challenge.expires_at.isoformat(),
            )

    token, _session = auth_service.create_session(
        db, user, client_ip(request), request.headers.get("user-agent")
    )
    db.commit()
    return LoginResponse(access_token=token)


@router.get("/mfa/challenge/{challenge_id}/status")
def mfa_challenge_status(
    challenge_id: uuid.UUID,
    db: Session = Depends(get_configured_db),
):
    return mfa_service.get_challenge_status(db, challenge_id)


@router.post("/mfa/verify", response_model=LoginResponse)
def mfa_verify_login(
    body: MfaVerifyLoginIn,
    request: Request,
    db: Session = Depends(get_configured_db),
) -> LoginResponse:
    from app.models.mfa import CoreMFAChallenge

    challenge = db.get(CoreMFAChallenge, body.challenge_id)
    if not challenge:
        raise SolaceHTTPException(400, "Invalid MFA challenge", code="MFA_NO_CHALLENGE")
    user = db.get(CoreUser, challenge.user_id)
    if not user:
        raise SolaceHTTPException(404, "User not found")
    mfa_service.verify_email_otp(
        db,
        user.id,
        body.otp,
        client_ip(request),
        challenge_id=body.challenge_id,
    )
    token, _session = auth_service.create_session(
        db, user, client_ip(request), request.headers.get("user-agent")
    )
    db.commit()
    return LoginResponse(access_token=token)


@router.post("/mfa/resend")
def mfa_resend_login(
    body: MfaResendLoginIn,
    request: Request,
    db: Session = Depends(get_configured_db),
):
    challenge = mfa_service.resend_login_challenge(
        db, body.challenge_id, client_ip(request), request.headers.get("user-agent")
    )
    db.commit()
    status = mfa_service.get_challenge_status(db, challenge.id)
    return status


@router.post("/logout")
def logout(
    request: Request,
    db: Session = Depends(get_configured_db),
    user: CoreUser = Depends(get_current_user),
    creds=Depends(bearer_scheme),
):
    from app.core.security import decode_access_token

    jti = None
    if creds and creds.credentials:
        try:
            jti = decode_access_token(creds.credentials).get("jti")
        except ValueError:
            pass
    auth_service.logout_session(db, jti, user.id)
    db.commit()
    return {"success": True}


@router.get("/available-scopes")
def available_scopes(
    db: Session = Depends(get_configured_db),
    user: CoreUser = Depends(get_current_user),
):
    from app.services import scope_service

    return scope_service.available_scopes_for_user(db, user)


@router.post("/switch-scope")
def switch_scope(
    body: SwitchScopeIn,
    request: Request,
    db: Session = Depends(get_configured_db),
    user: CoreUser = Depends(get_current_user),
    creds=Depends(bearer_scheme),
):
    from app.services import scope_service

    jti = None
    if creds and creds.credentials:
        try:
            jti = decode_access_token(creds.credentials).get("jti")
        except ValueError:
            pass
    if not jti:
        raise SolaceHTTPException(400, "No session token", code="NO_SESSION")
    session = db.scalar(select(CoreSession).where(CoreSession.token_jti == jti))
    if not session:
        raise SolaceHTTPException(401, "Session not found", code="UNAUTHORIZED")
    active = scope_service.switch_scope(
        db,
        user,
        session,
        scope_type=body.scope_type,
        country_id=body.country_id,
        organization_id=body.organization_id,
        branch_id=body.branch_id,
        department_id=body.department_id,
        ip_address=client_ip(request),
    )
    org_id = active.organization_id or user.organization_id
    token = create_access_token(
        str(user.id),
        str(org_id),
        settings.token_expiry_minutes,
        extra={"jti": jti},
        scope_type=active.scope_type,
        country_id=str(active.country_id) if active.country_id else None,
        branch_id=str(active.branch_id) if active.branch_id else None,
        department_id=str(active.department_id) if active.department_id else None,
    )
    set_organization_id(org_id)
    set_active_scope(active)
    db.commit()
    return {
        "access_token": token,
        "token_type": "bearer",
        "active_scope": {**active.to_dict(), "label": scope_service._scope_label_from_active(db, active)},
    }


@router.get("/me", response_model=MeResponse)
def me(
    db: Session = Depends(get_configured_db),
    user: CoreUser = Depends(get_current_user),
) -> MeResponse:
    from app.core.permissions import get_user_permission_codes
    from app.core.scope_context import get_active_scope
    from app.services import bootstrap_store, scope_service

    active = get_active_scope()
    perms = sorted(get_user_permission_codes(db, user, active))
    if "*" in perms:
        perms = ["*"]
    available = scope_service.available_scopes_for_user(db, user)
    active_out = None
    if active:
        active_out = ActiveScopeOut(
            scope_type=active.scope_type,
            country_id=str(active.country_id) if active.country_id else None,
            organization_id=str(active.organization_id) if active.organization_id else None,
            branch_id=str(active.branch_id) if active.branch_id else None,
            department_id=str(active.department_id) if active.department_id else None,
            label=scope_service._scope_label_from_active(db, active),
        )
    return MeResponse(
        id=str(user.id),
        username=user.username,
        email=user.email,
        display_name=user.display_name,
        is_admin=user.is_admin,
        organization_id=str(active.organization_id if active and active.organization_id else user.organization_id),
        mfa_enabled=user.mfa_enabled,
        permissions=perms,
        setup_complete=bootstrap_store.is_setup_complete(),
        active_scope=active_out,
        available_scopes=[
            ActiveScopeOut(
                scope_type=s["scope_type"],
                country_id=s.get("country_id"),
                organization_id=s.get("organization_id"),
                branch_id=s.get("branch_id"),
                department_id=s.get("department_id"),
                label=s.get("label"),
            )
            for s in available
        ],
    )
