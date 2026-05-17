"""MFA challenge endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import client_ip, get_configured_db, require_permission
from app.models.platform import CoreUser
from app.schemas.mfa import MfaChallengeCreateIn, MfaChallengeOut, MfaResendIn, MfaVerifyIn
from app.services import mfa_service

router = APIRouter(prefix="/mfa", tags=["mfa"])


@router.post("/challenges", response_model=MfaChallengeOut)
def create_challenge(
    body: MfaChallengeCreateIn,
    request: Request,
    db: Session = Depends(get_configured_db),
    admin: CoreUser = Depends(require_permission("mfa.update")),
):
    from app.core.exceptions import SolaceHTTPException

    user = db.get(CoreUser, body.user_id)
    if not user:
        raise SolaceHTTPException(404, "User not found")
    challenge = mfa_service.create_email_otp_challenge(
        db, user, client_ip(request), request.headers.get("user-agent")
    )
    db.commit()
    return MfaChallengeOut(
        challenge_id=str(challenge.id),
        destination_masked=challenge.destination_masked,
        expires_at=challenge.expires_at.isoformat(),
    )


@router.post("/challenges/verify")
def verify_challenge(
    body: MfaVerifyIn,
    request: Request,
    db: Session = Depends(get_configured_db),
):
    ok = mfa_service.verify_email_otp(db, body.user_id, body.otp, client_ip(request))
    db.commit()
    return {"success": ok}


@router.post("/challenges/resend", response_model=MfaChallengeOut)
def resend_challenge(
    body: MfaResendIn,
    request: Request,
    db: Session = Depends(get_configured_db),
    _admin: CoreUser = Depends(require_permission("mfa.update")),
):
    challenge = mfa_service.resend_email_otp_challenge(
        db, body.user_id, client_ip(request), request.headers.get("user-agent")
    )
    db.commit()
    return MfaChallengeOut(
        challenge_id=str(challenge.id),
        destination_masked=challenge.destination_masked,
        expires_at=challenge.expires_at.isoformat(),
    )
