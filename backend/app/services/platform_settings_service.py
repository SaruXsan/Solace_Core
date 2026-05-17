"""Read/write platform security, system, and database status settings."""

from __future__ import annotations

import json
import re
import uuid
from urllib.parse import unquote_plus

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings as app_settings
from app.core.crypto import mask_secret
from app.models.settings import CoreSecuritySettings
from app.services import bootstrap_store, settings_service
from app.services.setup_service import test_sql_connection


def get_or_create_security_settings(db: Session) -> CoreSecuritySettings:
    row = db.scalar(select(CoreSecuritySettings).limit(1))
    if row is None:
        row = CoreSecuritySettings()
        db.add(row)
        db.flush()
    return row


def get_system_settings(db: Session) -> dict:
    sec = get_or_create_security_settings(db)
    return {
        "app_display_name": sec.app_display_name,
        "environment_label": sec.environment_label,
        "session_timeout_minutes": sec.session_timeout_minutes,
        "login_max_attempts": sec.login_max_attempts,
        "login_lockout_minutes": sec.login_lockout_minutes,
    }


def update_system_settings(db: Session, data: dict) -> CoreSecuritySettings:
    sec = get_or_create_security_settings(db)
    for key in (
        "app_display_name",
        "environment_label",
        "session_timeout_minutes",
        "login_max_attempts",
        "login_lockout_minutes",
    ):
        if key in data and data[key] is not None:
            setattr(sec, key, data[key])
            if key == "session_timeout_minutes":
                app_settings.session_timeout_minutes = data[key]
                app_settings.token_expiry_minutes = data[key]
            elif key == "login_max_attempts":
                app_settings.login_max_attempts = data[key]
            elif key == "login_lockout_minutes":
                app_settings.login_lockout_minutes = data[key]
    return sec


def get_database_status() -> dict:
    url = bootstrap_store.get_db_connection_url()
    if not url:
        return {
            "configured": False,
            "connected": False,
            "message": "Database not configured",
        }
    result = test_sql_connection(url)
    server_hint, db_name = _parse_connection_hints(url)
    return {
        "configured": True,
        "connected": result.get("success", False),
        "server_hint": server_hint,
        "database_name": db_name,
        "message": result.get("message"),
    }


def _parse_connection_hints(url: str) -> tuple[str | None, str | None]:
    try:
        if "odbc_connect=" in url:
            odbc = unquote_plus(url.split("odbc_connect=", 1)[1])
            server = re.search(r"SERVER=([^;]+)", odbc, re.I)
            database = re.search(r"DATABASE=([^;]+)", odbc, re.I)
            return (
                server.group(1) if server else "configured",
                database.group(1) if database else None,
            )
    except Exception:
        pass
    return "configured", None


def get_mfa_settings(db: Session) -> dict:
    sec = get_or_create_security_settings(db)
    has_pw = settings_service.get_encrypted_setting(db, "smtp_password") is not None
    masked = settings_service.get_encrypted_masked(db, "smtp_password")
    return {
        "enable_mfa": sec.enable_mfa,
        "require_mfa_for_admins": sec.require_mfa_for_admins,
        "otp_expiry_minutes": sec.otp_expiry_minutes,
        "otp_retry_limit": sec.otp_retry_limit,
        "resend_cooldown_seconds": sec.resend_cooldown_seconds,
        "smtp_host": sec.smtp_host,
        "smtp_port": sec.smtp_port,
        "smtp_use_tls": sec.smtp_use_tls,
        "smtp_username": sec.smtp_username,
        "from_email": sec.from_email,
        "has_smtp_password": has_pw,
        "smtp_password_masked": masked,
    }


def update_mfa_settings(
    db: Session, data: dict, updated_by: uuid.UUID | None = None
) -> CoreSecuritySettings:
    sec = get_or_create_security_settings(db)
    for key in (
        "enable_mfa",
        "require_mfa_for_admins",
        "otp_expiry_minutes",
        "otp_retry_limit",
        "resend_cooldown_seconds",
        "smtp_host",
        "smtp_port",
        "smtp_use_tls",
        "smtp_username",
        "from_email",
    ):
        if key in data and data[key] is not None:
            setattr(sec, key, data[key])
            if key == "otp_expiry_minutes":
                app_settings.mfa_otp_expiry_minutes = data[key]
            elif key == "otp_retry_limit":
                app_settings.mfa_otp_max_attempts = data[key]
            elif key == "resend_cooldown_seconds":
                app_settings.mfa_resend_cooldown_seconds = data[key]
    if data.get("smtp_password"):
        settings_service.set_encrypted_setting(
            db, "smtp_password", data["smtp_password"], updated_by=updated_by
        )
    return sec


def test_smtp_email(
    db: Session, to_address: str, actor_id: uuid.UUID | None = None
) -> dict:
    """Send a test email; never log credentials or message body secrets."""
    import logging
    import smtplib
    from email.mime.text import MIMEText

    from app.services import audit_service

    logger = logging.getLogger(__name__)
    sec = get_or_create_security_settings(db)
    password = settings_service.get_encrypted_setting(db, "smtp_password")
    if not sec.smtp_host or not password:
        return {
            "success": False,
            "message": "SMTP host or password not configured",
        }
    sender = sec.from_email or sec.smtp_username or "noreply@solace.local"
    try:
        body = MIMEText(
            "This is a Solace Enterprise Core SMTP test message. "
            "If you received this, outbound email is configured correctly."
        )
        body["Subject"] = "Solace SMTP test"
        body["From"] = sender
        body["To"] = to_address
        if sec.smtp_use_tls:
            server = smtplib.SMTP(sec.smtp_host, sec.smtp_port, timeout=15)
            server.starttls()
        else:
            server = smtplib.SMTP(sec.smtp_host, sec.smtp_port, timeout=15)
        server.login(sec.smtp_username or "", password)
        server.sendmail(sender, [to_address], body.as_string())
        server.quit()
        logger.info("SMTP test email sent", extra={"to_domain": to_address.split("@")[-1]})
        if actor_id:
            audit_service.log_audit(
                db,
                "smtp",
                "test_email_success",
                actor_user_id=actor_id,
                detail={"to": to_address.split("@")[-1]},
            )
        return {"success": True, "message": f"Test email sent to {to_address}"}
    except Exception as exc:
        safe = _classify_smtp_error(exc)
        logger.warning("SMTP test failed", extra={"error_type": type(exc).__name__})
        if actor_id:
            audit_service.log_audit(
                db,
                "smtp",
                "test_email_failed",
                actor_user_id=actor_id,
                detail={"error_type": type(exc).__name__, "category": safe},
            )
        return {"success": False, "message": safe}


def _classify_smtp_error(exc: Exception) -> str:
    msg = str(exc).lower()
    name = type(exc).__name__.lower()
    if "authentication" in msg or "535" in msg or "credential" in msg:
        return "SMTP authentication failed. Check username and password."
    if "connection refused" in msg or "10061" in msg or "network" in msg:
        return "Cannot connect to SMTP host. Check host, port, and firewall."
    if "timed out" in msg or "timeout" in name:
        return "SMTP connection timed out."
    if "starttls" in msg or "tls" in msg or "ssl" in msg:
        return "TLS/STARTTLS negotiation failed. Verify SMTP TLS settings."
    if "recipient" in msg or "550" in msg or "553" in msg:
        return "Invalid sender or recipient address."
    return "SMTP delivery failed. Verify configuration (details not logged)."


def apply_security_settings_to_runtime(db: Session) -> None:
    """Sync DB security settings into in-memory app config."""
    sec = get_or_create_security_settings(db)
    app_settings.mfa_otp_expiry_minutes = sec.otp_expiry_minutes
    app_settings.mfa_otp_max_attempts = sec.otp_retry_limit
    app_settings.mfa_resend_cooldown_seconds = sec.resend_cooldown_seconds
    app_settings.session_timeout_minutes = sec.session_timeout_minutes
    app_settings.token_expiry_minutes = sec.session_timeout_minutes
    app_settings.login_max_attempts = sec.login_max_attempts
    app_settings.login_lockout_minutes = sec.login_lockout_minutes
