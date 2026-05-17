from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_configured_db, require_permission
from app.models.platform import CoreUser
from app.services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats")
def stats(
    db: Session = Depends(get_configured_db),
    _user: CoreUser = Depends(require_permission("dashboard.read")),
):
    return dashboard_service.get_dashboard_stats(db)
