"""First-run setup — SQL Server test, migrations, admin creation."""

from __future__ import annotations

import logging
from urllib.parse import quote_plus

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.database import init_engine
from app.core.exceptions import SolaceHTTPException
from app.models.platform import CoreOrganization
from app.services import audit_service, auth_service, bootstrap_store, seed_service

logger = logging.getLogger(__name__)


def build_mssql_url(
    server: str,
    database: str,
    username: str = "",
    password: str = "",
    driver: str = "ODBC Driver 18 for SQL Server",
    trust_cert: bool = True,
    use_trusted_connection: bool = False,
) -> str:
    if use_trusted_connection:
        odbc = (
            f"DRIVER={{{driver}}};"
            f"SERVER={server};"
            f"DATABASE={database};"
            "Trusted_Connection=yes;"
        )
    else:
        odbc = (
            f"DRIVER={{{driver}}};"
            f"SERVER={server};"
            f"DATABASE={database};"
            f"UID={username};"
            f"PWD={password};"
        )
    if trust_cert:
        odbc += "TrustServerCertificate=yes;"
    return f"mssql+pyodbc:///?odbc_connect={quote_plus(odbc)}"


def test_sql_connection(url: str) -> dict:
    try:
        engine = create_engine(url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return {"success": True, "message": "SQL Server connection successful"}
    except SQLAlchemyError as e:
        logger.warning("SQL connection test failed")
        return {"success": False, "message": str(e)[:300]}


def initialize_database(url: str) -> None:
    bootstrap_store.save_database_url(url)
    init_engine(url)


def complete_setup(
    db: Session,
    org_name: str,
    org_code: str,
    admin_email: str,
    admin_username: str,
    admin_password: str,
    admin_display_name: str,
    ip_address: str | None = None,
) -> dict:
    if bootstrap_store.is_setup_complete():
        raise SolaceHTTPException(400, "Setup already completed", code="SETUP_DONE")

    org = CoreOrganization(name=org_name, code=org_code, is_active=True)
    db.add(org)
    db.flush()

    admin = auth_service.create_admin_user(
        db,
        org.id,
        admin_email,
        admin_username,
        admin_password,
        admin_display_name,
    )
    seed_service.seed_foundation_data(db)
    from app.models.platform import CoreRole, CoreUserRole
    from sqlalchemy import select

    sys_role = db.scalar(
        select(CoreRole).where(
            CoreRole.organization_id == org.id,
            CoreRole.code == "system_administrator",
        )
    )
    if sys_role:
        db.add(CoreUserRole(user_id=admin.id, role_id=sys_role.id))
    bootstrap_store.mark_setup_complete()

    audit_service.log_audit(
        db,
        "setup",
        "first_run_complete",
        actor_user_id=admin.id,
        organization_id=org.id,
        detail={"org_code": org_code},
        ip_address=ip_address,
    )
    return {
        "organization_id": str(org.id),
        "admin_user_id": str(admin.id),
        "message": "Setup completed successfully",
    }
