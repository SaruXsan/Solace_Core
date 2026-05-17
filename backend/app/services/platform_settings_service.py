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
