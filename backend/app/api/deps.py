"""FastAPI dependencies."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import SetupRequiredException, SolaceHTTPException
from app.core.security import decode_access_token
from app.core.scope_context import ActiveScope, set_active_scope
from app.core.tenant_context import set_organization_id
from app.models.platform import CoreSession, CoreUser
from app.services import bootstrap_store

bearer_scheme = HTTPBearer(auto_error=False)


def require_db_configured() -> None:
    if not bootstrap_store.get_db_connection_url():
        raise SetupRequiredException()


def get_configured_db() -> Session:
    require_db_configured()
    yield from get_db()


async def get_current_user(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_configured_db)],
) -> CoreUser:
    if creds is None:
        raise SolaceHTTPException(401, "Not authenticated", code="UNAUTHORIZED")
    try:
        payload = decode_access_token(creds.credentials)
    except ValueError as e:
        raise SolaceHTTPException(401, "Invalid token", code="UNAUTHORIZED") from e
    user_id = UUID(payload["sub"])
    jti = payload.get("jti")
    user = db.scalar(
        select(CoreUser).where(CoreUser.id == user_id, CoreUser.is_active == True)  # noqa: E712
    )
    if user is None:
        raise SolaceHTTPException(401, "User not found", code="UNAUTHORIZED")
    if jti:
        session = db.scalar(
            select(CoreSession).where(
                CoreSession.token_jti == jti,
                CoreSession.revoked_at.is_(None),
            )
        )
        if session is None:
            raise SolaceHTTPException(401, "Session revoked", code="SESSION_REVOKED")
        if session.expires_at < datetime.now(timezone.utc):
            raise SolaceHTTPException(401, "Session expired", code="SESSION_EXPIRED")
        scope = ActiveScope(
            scope_type=session.active_scope_type or "organization",
            country_id=session.active_country_id,
            organization_id=session.organization_id,
            branch_id=session.active_branch_id,
            department_id=session.active_department_id,
        )
        set_active_scope(scope)
        set_organization_id(session.organization_id)
        from app.services import consolidation_scope_service as css

        css.load_session_consolidation(db, session)
    else:
        set_organization_id(user.organization_id)
    return user


async def require_admin(user: Annotated[CoreUser, Depends(get_current_user)]) -> CoreUser:
    """Bootstrap / emergency use only — prefer require_permission() on platform routes."""
    if not user.is_admin:
        raise SolaceHTTPException(403, "Admin access required", code="FORBIDDEN")
    return user


def require_permission(*codes: str):
    """FastAPI dependency: user must hold at least one of the given permission codes."""

    async def _checker(
        request: Request,
        user: Annotated[CoreUser, Depends(get_current_user)],
        db: Annotated[Session, Depends(get_configured_db)],
    ) -> CoreUser:
        from app.core.permissions import assert_any_permission

        assert_any_permission(db, user, *codes, ip_address=client_ip(request))
        return user

    return _checker


def client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None
