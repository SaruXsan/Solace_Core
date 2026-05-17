"""Authentication endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import bearer_scheme, client_ip, get_configured_db, get_current_user
from app.core.exceptions import SolaceHTTPException
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


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    display_name: str
    is_admin: bool
    organization_id: str
    mfa_enabled: bool
    permissions: list[str] = []


class MeResponse(UserResponse):
    setup_complete: bool = True


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
        if not body.mfa_otp:
            challenge = mfa_service.create_email_otp_challenge(
                db, user, client_ip(request), request.headers.get("user-agent")
            )
            db.commit()
            return LoginResponse(
                access_token="",
                mfa_required=True,
                challenge_id=str(challenge.id),
            )
        mfa_service.verify_email_otp(db, user.id, body.mfa_otp, client_ip(request))

    token, _session = auth_service.create_session(
        db, user, client_ip(request), request.headers.get("user-agent")
    )
    db.commit()
    return LoginResponse(access_token=token)


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


@router.get("/me", response_model=MeResponse)
def me(
    db: Session = Depends(get_configured_db),
    user: CoreUser = Depends(get_current_user),
) -> MeResponse:
    from app.core.permissions import get_user_permission_codes
    from app.services import bootstrap_store

    perms = sorted(get_user_permission_codes(db, user))
    if "*" in perms:
        perms = ["*"]
    return MeResponse(
        id=str(user.id),
        username=user.username,
        email=user.email,
        display_name=user.display_name,
        is_admin=user.is_admin,
        organization_id=str(user.organization_id),
        mfa_enabled=user.mfa_enabled,
        permissions=perms,
        setup_complete=bootstrap_store.is_setup_complete(),
    )
