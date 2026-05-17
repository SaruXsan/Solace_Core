"""Email OTP MFA foundation."""

from __future__ import annotations

import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.crypto import hash_otp
from app.core.exceptions import SolaceHTTPException
from app.models.mfa import CoreMFAChallenge
from app.models.platform import CoreUser
from app.services import audit_service, platform_settings_service

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _mask_email(email: str) -> str:
    local, _, domain = email.partition("@")
    if len(local) <= 2:
        return f"**@{domain}"
    return f"{local[0]}***{local[-1]}@{domain}"


def _load_mfa_policy(db: Session) -> None:
    platform_settings_service.apply_security_settings_to_runtime(db)


def user_requires_mfa(db: Session, user: CoreUser) -> bool:
    _load_mfa_policy(db)
    sec = platform_settings_service.get_or_create_security_settings(db)
    if sec.enable_mfa and user.mfa_enabled:
        return True
    if sec.require_mfa_for_admins and user.is_admin:
        return True
    if user.is_privileged_account:
        return True
    if user.mfa_enabled:
        return True
    # Role-based check would query Core_UserRoles + Core_Roles.requires_mfa
    from app.models.platform import CoreRole, CoreUserRole

    role_requires = db.scalar(
        select(CoreRole.requires_mfa)
        .join(CoreUserRole, CoreUserRole.role_id == CoreRole.id)
        .where(CoreUserRole.user_id == user.id, CoreRole.requires_mfa == True)  # noqa: E712
        .limit(1)
    )
    return bool(role_requires)


def resend_email_otp_challenge(
    db: Session, user_id: uuid.UUID, ip: str | None, ua: str | None
) -> CoreMFAChallenge:
    user = db.get(CoreUser, user_id)
    if not user:
        raise SolaceHTTPException(404, "User not found")
    return create_email_otp_challenge(db, user, ip, ua, is_resend=True)


def create_email_otp_challenge(
    db: Session,
    user: CoreUser,
    ip: str | None,
    ua: str | None,
    is_resend: bool = False,
) -> CoreMFAChallenge:
    _load_mfa_policy(db)
    sec = platform_settings_service.get_or_create_security_settings(db)
    # Check resend cooldown
    recent = db.scalar(
        select(CoreMFAChallenge)
        .where(
            CoreMFAChallenge.user_id == user.id,
            CoreMFAChallenge.consumed_at.is_(None),
        )
        .order_by(CoreMFAChallenge.created_at.desc())
    )
    if recent and recent.last_resend_at:
        elapsed = (_utcnow() - recent.last_resend_at).total_seconds()
        cooldown = sec.resend_cooldown_seconds
        if elapsed < cooldown:
            raise SolaceHTTPException(
                429,
                f"Resend cooldown active ({int(cooldown - elapsed)}s remaining)",
                code="MFA_COOLDOWN",
            )

    otp = f"{secrets.randbelow(1_000_000):06d}"
    salt = secrets.token_hex(16)
    challenge = CoreMFAChallenge(
        user_id=user.id,
        challenge_type="email_otp",
        destination_masked=_mask_email(user.email),
        otp_hash=hash_otp(otp, salt),
        otp_salt=salt,
        expires_at=_utcnow() + timedelta(minutes=sec.otp_expiry_minutes),
        max_attempts=sec.otp_retry_limit,
        ip_address=ip,
        user_agent=ua,
        last_resend_at=_utcnow(),
    )
    db.add(challenge)
    db.flush()

    # OTP delivery skeleton — log masked only, never OTP value
    logger.info(
        "MFA OTP sent",
        extra={"user_id": str(user.id), "destination": challenge.destination_masked},
    )
    # In production: integrate SMTP; for foundation store in audit only
    event = "otp_resent" if is_resend else "otp_sent"
    audit_service.log_mfa_event(db, user.id, event, True, challenge_id=challenge.id, ip_address=ip)
    _send_otp_email(db, user.email, otp, sec)

    return challenge


def _send_otp_email(db: Session, to_email: str, otp: str, sec) -> None:
    """Send OTP via SMTP if configured; never log OTP value."""
    from app.services import settings_service

    password = settings_service.get_encrypted_setting(db, "smtp_password")
    if not sec.smtp_host or not password:
        logger.info("MFA OTP email skipped (SMTP not configured)", extra={"to": _mask_email(to_email)})
        return
    try:
        import smtplib
        from email.mime.text import MIMEText

        sender = sec.from_email or sec.smtp_username or "noreply@solace.local"
        body = MIMEText(
            f"Your Solace verification code is: {otp}\n\n"
            f"Expires in {sec.otp_expiry_minutes} minutes."
        )
        body["Subject"] = "Solace verification code"
        body["From"] = sender
        body["To"] = to_email
        if sec.smtp_use_tls:
            server = smtplib.SMTP(sec.smtp_host, sec.smtp_port, timeout=15)
            server.starttls()
        else:
            server = smtplib.SMTP(sec.smtp_host, sec.smtp_port, timeout=15)
        server.login(sec.smtp_username or "", password)
        server.sendmail(sender, [to_email], body.as_string())
        server.quit()
        logger.info("MFA OTP email sent", extra={"to": _mask_email(to_email)})
    except Exception:
        logger.warning("MFA OTP email delivery failed", extra={"to": _mask_email(to_email)})


def verify_email_otp(
    db: Session,
    user_id: uuid.UUID,
    otp: str,
    ip: str | None = None,
) -> bool:
    challenge = db.scalar(
        select(CoreMFAChallenge)
        .where(
            CoreMFAChallenge.user_id == user_id,
            CoreMFAChallenge.consumed_at.is_(None),
        )
        .order_by(CoreMFAChallenge.created_at.desc())
    )
    if challenge is None:
        audit_service.log_mfa_event(db, user_id, "verify_failed", False, ip_address=ip)
        raise SolaceHTTPException(400, "No active MFA challenge", code="MFA_NO_CHALLENGE")

    if challenge.expires_at < _utcnow():
        audit_service.log_mfa_event(
            db, user_id, "otp_expired", False, challenge_id=challenge.id, ip_address=ip
        )
        raise SolaceHTTPException(400, "OTP expired", code="MFA_EXPIRED")

    if challenge.attempts_count >= challenge.max_attempts:
        audit_service.log_mfa_event(
            db, user_id, "otp_locked", False, challenge_id=challenge.id, ip_address=ip
        )
        raise SolaceHTTPException(429, "Too many MFA attempts", code="MFA_LOCKED")

    expected = hash_otp(otp, challenge.otp_salt)
    if expected != challenge.otp_hash:
        challenge.attempts_count += 1
        audit_service.log_mfa_event(
            db, user_id, "verify_failed", False, challenge_id=challenge.id, ip_address=ip
        )
        raise SolaceHTTPException(401, "Invalid OTP", code="MFA_INVALID")

    challenge.consumed_at = _utcnow()
    audit_service.log_mfa_event(
        db, user_id, "verify_success", True, challenge_id=challenge.id, ip_address=ip
    )
    return True
