"""First-run setup endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import client_ip, get_configured_db
from app.core.database import get_db
from app.services import bootstrap_store, setup_service

router = APIRouter(prefix="/setup", tags=["setup"])


class SetupStatusResponse(BaseModel):
    needs_setup: bool
    master_key_configured: bool = True
    database_configured: bool


class TestDbRequest(BaseModel):
    server: str
    database: str
    username: str = ""
    password: str = ""
    driver: str = "ODBC Driver 18 for SQL Server"
    trust_server_certificate: bool = True
    use_trusted_connection: bool = False


class SaveDbRequest(TestDbRequest):
    pass


class CompleteSetupRequest(BaseModel):
    organization_name: str = Field(min_length=2)
    organization_code: str = Field(min_length=2, max_length=64)
    admin_email: str
    admin_username: str = Field(min_length=3)
    admin_password: str = Field(min_length=12)
    admin_display_name: str


@router.get("/status", response_model=SetupStatusResponse)
def setup_status() -> SetupStatusResponse:
    db_configured = bootstrap_store.get_db_connection_url() is not None
    needs = not bootstrap_store.is_setup_complete()
    return SetupStatusResponse(
        needs_setup=needs,
        database_configured=db_configured,
    )


@router.post("/test-database")
def test_database(body: TestDbRequest) -> dict:
    url = setup_service.build_mssql_url(
        body.server,
        body.database,
        body.username,
        body.password,
        body.driver,
        body.trust_server_certificate,
        body.use_trusted_connection,
    )
    return setup_service.test_sql_connection(url)


@router.post("/run-migrations")
def run_migrations() -> dict:
    """Apply Alembic foundation migration (requires saved database)."""
    import subprocess
    import sys
    from pathlib import Path

    if not bootstrap_store.get_db_connection_url():
        return {"success": False, "message": "Save database connection first"}
    root = Path(__file__).resolve().parents[4]
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", str(root / "alembic.ini"), "upgrade", "head"],
        cwd=str(root),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return {"success": False, "message": result.stderr[-500:] or result.stdout[-500:]}
    return {"success": True, "message": "Migrations applied"}


@router.post("/save-database")
def save_database(body: SaveDbRequest) -> dict:
    url = setup_service.build_mssql_url(
        body.server,
        body.database,
        body.username,
        body.password,
        body.driver,
        body.trust_server_certificate,
        body.use_trusted_connection,
    )
    result = setup_service.test_sql_connection(url)
    if not result["success"]:
        return result
    setup_service.initialize_database(url)
    return {"success": True, "message": "Database connection saved"}


@router.post("/complete")
def complete_setup(
    body: CompleteSetupRequest,
    request: Request,
    db: Session = Depends(get_configured_db),
) -> dict:
    return setup_service.complete_setup(
        db,
        body.organization_name,
        body.organization_code,
        body.admin_email,
        body.admin_username,
        body.admin_password,
        body.admin_display_name,
        ip_address=client_ip(request),
    )
