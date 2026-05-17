"""Local authentication, lockout, sessions."""

from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AccountLockedException, SolaceHTTPException
from app.core.security import (
    create_access_token,
    hash_password,
    validate_password_strength,
    verify_password,
)
from app.core.tenant_context import set_organization_id
from app.models.platform import CoreLoginAttempt, CoreSession, CoreUser
from app.services import audit_service


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def check_account_locked(user: CoreUser) -> None:
    if user.locked_until and user.locked_until > _utcnow():
        raise AccountLockedException(user.locked_until.isoformat())


def record_failed_login(
    db: Session,
    user: CoreUser | None,
    username: str,
    ip: str | None,
    auth_source: str = "local",
) -> None:
    db.add(
        CoreLoginAttempt(
            username=username,
            ip_address=ip,
            success=False,
            auth_source=auth_source,
            failure_reason="invalid_credentials",
        )
    )
    if user is None:
        return
    user.failed_login_count = (user.failed_login_count or 0) + 1
    if user.failed_login_count >= settings.login_max_attempts:
        user.locked_until = _utcnow() + timedelta(minutes=settings.login_lockout_minutes)
        user.failed_login_count = 0
        audit_service.log_audit(
            db,
            "security",
            "account_locked",
            actor_user_id=user.id,
            organization_id=user.organization_id,
            detail={"minutes": settings.login_lockout_minutes},
            ip_address=ip,
        )


def authenticate_local(
    db: Session,
    username: str,
    password: str,
    ip_address: str | None = None,
) -> CoreUser:
    user = db.scalar(
        select(CoreUser).where(
            CoreUser.username == username,
            CoreUser.deleted_at.is_(None),
            CoreUser.is_active == True,  # noqa: E712 — SQL Server compat
        )
    )
    if user is None:
        record_failed_login(db, None, username, ip_address)
        audit_service.log_login(
            db, username, "local", False, failure_reason="user_not_found", ip_address=ip_address
        )
        raise SolaceHTTPException(401, "Invalid username or password", code="AUTH_FAILED")

    check_account_locked(user)

    if not user.password_hash or not verify_password(password, user.password_hash):
        record_failed_login(db, user, username, ip_address)
        audit_service.log_login(
            db,
            username,
            "local",
            False,
            user_id=user.id,
            failure_reason="bad_password",
            ip_address=ip_address,
        )
        raise SolaceHTTPException(401, "Invalid username or password", code="AUTH_FAILED")

    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = _utcnow()
    audit_service.log_login(
        db, username, "local", True, user_id=user.id, ip_address=ip_address
    )
    return user


def authenticate_user(
    db: Session,
    username: str,
    password: str,
    ip_address: str | None = None,
) -> CoreUser:
    """Local first; LDAP/LDAPS when directory enabled and local password fails or user is directory-only."""
    from app.services import ldap_service

    user = db.scalar(
        select(CoreUser).where(
            CoreUser.username == username,
            CoreUser.deleted_at.is_(None),
            CoreUser.is_active == True,  # noqa: E712
        )
    )
    if user and user.password_hash and not user.is_directory_user:
        try:
            return authenticate_local(db, username, password, ip_address)
        except SolaceHTTPException:
            pass

    dir_row = ldap_service.get_directory_settings(db)
    if dir_row and dir_row.directory_enabled:
        attrs = ldap_service.authenticate_directory_user(db, username, password)
        if attrs:
            auth_src = attrs.get("auth_source", "LDAP")
            if user is None:
                from app.models.platform import CoreOrganization

                org = db.scalar(select(CoreOrganization).limit(1))
                if not org:
                    raise SolaceHTTPException(503, "No organization configured")
                user = CoreUser(
                    organization_id=org.id,
                    username=username,
                    email=attrs.get("email", f"{username}@local"),
                    display_name=attrs.get("display_name", username),
                    directory_source=auth_src,
                    is_directory_user=True,
                    directory_object_id=attrs.get("directory_object_id"),
                    is_active=True,
                )
                db.add(user)
                db.flush()
            else:
                user.directory_source = auth_src
                user.is_directory_user = True
                user.directory_object_id = attrs.get("directory_object_id")
            user.failed_login_count = 0
            user.locked_until = None
            user.last_login_at = _utcnow()
            audit_service.log_login(
                db, username, auth_src, True, user_id=user.id, ip_address=ip_address
            )
            return user

    if user is None:
        record_failed_login(db, None, username, ip_address)
        audit_service.log_login(
            db, username, "local", False, failure_reason="user_not_found", ip_address=ip_address
        )
    raise SolaceHTTPException(401, "Invalid username or password", code="AUTH_FAILED")


def logout_session(db: Session, jti: str | None, user_id: uuid.UUID) -> None:
    if jti:
        session = db.scalar(select(CoreSession).where(CoreSession.token_jti == jti))
        if session:
            session.revoked_at = _utcnow()
    audit_service.log_audit(db, "auth", "logout", actor_user_id=user_id)


def create_session(
    db: Session,
    user: CoreUser,
    ip_address: str | None,
    user_agent: str | None,
) -> tuple[str, CoreSession]:
    jti = secrets.token_hex(16)
    expires = _utcnow() + timedelta(minutes=settings.token_expiry_minutes)
    token = create_access_token(
        str(user.id),
        str(user.organization_id),
        settings.token_expiry_minutes,
        extra={"jti": jti},
    )
    session = CoreSession(
        user_id=user.id,
        organization_id=user.organization_id,
        token_jti=jti,
        ip_address=ip_address,
        user_agent=user_agent,
        expires_at=expires,
    )
    db.add(session)
    set_organization_id(user.organization_id)
    return token, session


def create_admin_user(
    db: Session,
    organization_id: uuid.UUID,
    email: str,
    username: str,
    password: str,
    display_name: str,
) -> CoreUser:
    errors = validate_password_strength(password)
    if errors:
        raise SolaceHTTPException(400, "; ".join(errors), code="WEAK_PASSWORD")
    user = CoreUser(
        organization_id=organization_id,
        email=email,
        username=username,
        password_hash=hash_password(password),
        display_name=display_name,
        is_admin=True,
        is_active=True,
        directory_source="local",
    )
    db.add(user)
    db.flush()
    return user
