from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_configured_db, require_permission
from app.models.platform import CoreUser
from app.services import log_query_service

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("/audit-trail")
def audit_trail(
    limit: int = Query(100, le=500),
    db: Session = Depends(get_configured_db),
    _user: CoreUser = Depends(require_permission("audit.read", "logs.read")),
):
    return log_query_service.list_audit_trail(db, limit)


@router.get("/login-events")
def login_events(
    limit: int = Query(100, le=500),
    db: Session = Depends(get_configured_db),
    _user: CoreUser = Depends(require_permission("logs.read")),
):
    return log_query_service.list_login_events(db, limit)


@router.get("/admin-actions")
def admin_actions(
    limit: int = Query(100, le=500),
    db: Session = Depends(get_configured_db),
    _user: CoreUser = Depends(require_permission("logs.read")),
):
    return log_query_service.list_admin_actions(db, limit)


@router.get("/config-changes")
def config_changes(
    limit: int = Query(100, le=500),
    db: Session = Depends(get_configured_db),
    _user: CoreUser = Depends(require_permission("logs.read")),
):
    return log_query_service.list_config_changes(db, limit)


@router.get("/permission-changes")
def permission_changes(
    limit: int = Query(100, le=500),
    db: Session = Depends(get_configured_db),
    _user: CoreUser = Depends(require_permission("logs.read", "permissions.manage")),
):
    return log_query_service.list_permission_changes(db, limit)


@router.get("/llm-calls")
def llm_calls(
    limit: int = Query(100, le=500),
    db: Session = Depends(get_configured_db),
    _user: CoreUser = Depends(require_permission("logs.read")),
):
    return log_query_service.list_llm_calls(db, limit)


@router.get("/posture-violations")
def posture_violations(
    limit: int = Query(100, le=500),
    db: Session = Depends(get_configured_db),
    _user: CoreUser = Depends(require_permission("logs.read")),
):
    return log_query_service.list_posture_violations(db, limit)


@router.get("/system-errors")
def system_errors(
    limit: int = Query(100, le=500),
    db: Session = Depends(get_configured_db),
    _user: CoreUser = Depends(require_permission("logs.read")),
):
    return log_query_service.list_system_errors(db, limit)
