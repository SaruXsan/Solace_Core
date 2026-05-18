"""Drop/recreate SolaceEnterpriseCore and run foundation setup (local dev)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from sqlalchemy import create_engine, text

from app.core.config import require_master_key
from app.core.database import init_engine, session_scope
from app.models.platform import CoreOrganization
from app.services import bootstrap_store, platform_settings_service, seed_service, setup_service
from app.services.auth_service import create_admin_user

require_master_key()

SERVER = os.environ.get("SOLACE_DB_SERVER", "localhost")
DATABASE = os.environ.get("SOLACE_DB_NAME", "SolaceEnterpriseCore")
USER = os.environ.get("SOLACE_DB_USER", "cursor")
PASSWORD = os.environ.get("SOLACE_DB_PASSWORD", "")
TRUSTED = os.environ.get("SOLACE_DB_TRUSTED", "1").strip().lower() in ("1", "true", "yes")
DRIVER = os.environ.get("SOLACE_ODBC_DRIVER", "ODBC Driver 17 for SQL Server")

ADMIN_USER = os.environ.get("SOLACE_ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("SOLACE_ADMIN_PASSWORD", "SolaceAdmin2026!")
ADMIN_EMAIL = os.environ.get("SOLACE_ADMIN_EMAIL", "admin@local")
ORG_NAME = os.environ.get("SOLACE_ORG_NAME", "Default Organization")
ORG_CODE = os.environ.get("SOLACE_ORG_CODE", "DEFAULT")

DATA_DIR = BACKEND / "data"
BOOTSTRAP = DATA_DIR / "bootstrap.enc"


def _url(database: str) -> str:
    if TRUSTED:
        return setup_service.build_mssql_url(
            SERVER, database, use_trusted_connection=True, driver=DRIVER
        )
    if not PASSWORD:
        raise SystemExit("Set SOLACE_DB_PASSWORD or SOLACE_DB_TRUSTED=1")
    return setup_service.build_mssql_url(
        SERVER, database, USER, PASSWORD, driver=DRIVER, trust_cert=True
    )


def main() -> None:
    if BOOTSTRAP.exists():
        BOOTSTRAP.unlink()
        print("Removed existing bootstrap.enc")

    master = create_engine(_url("master"), isolation_level="AUTOCOMMIT")
    with master.connect() as conn:
        row = conn.execute(
            text("SELECT database_id FROM sys.databases WHERE name = :db"),
            {"db": DATABASE},
        ).fetchone()
        if row:
            conn.execute(
                text(
                    f"ALTER DATABASE [{DATABASE}] SET SINGLE_USER WITH ROLLBACK IMMEDIATE"
                )
            )
            conn.execute(text(f"DROP DATABASE [{DATABASE}]"))
            print(f"Dropped database [{DATABASE}]")
        conn.execute(text(f"CREATE DATABASE [{DATABASE}]"))
        print(f"Created database [{DATABASE}]")
    master.dispose()

    app_url = _url(DATABASE)
    test = setup_service.test_sql_connection(app_url)
    if not test["success"]:
        raise SystemExit(f"Connection failed: {test['message']}")
    print("SQL connection OK")

    bootstrap_store.save_database_url(app_url)
    init_engine(app_url)
    print("Saved encrypted bootstrap connection")

    # 001 uses Base.metadata.create_all (current models). Later revisions only apply
    # on DBs that were created before those columns/tables existed.
    for args, label in (
        (["upgrade", "001_foundation"], "001_foundation"),
        (["stamp", "head"], "alembic head stamp"),
    ):
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "-c", str(ROOT / "alembic.ini"), *args],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(result.stderr or result.stdout)
            raise SystemExit(f"Alembic {label} failed")
    print("Schema created and alembic stamped to head")

    with session_scope() as db:
        org = CoreOrganization(name=ORG_NAME, code=ORG_CODE, is_active=True)
        db.add(org)
        db.flush()
        create_admin_user(
            db, org.id, ADMIN_EMAIL, ADMIN_USER, ADMIN_PASS, "System Administrator"
        )
        seed_service.seed_foundation_data(db)
        sec = platform_settings_service.get_or_create_security_settings(db)
        sec.enable_mfa = False
        sec.require_mfa_for_admins = False
        from app.models.platform import CoreRole
        from sqlalchemy import select

        for role in db.scalars(select(CoreRole).where(CoreRole.requires_mfa == True)).all():  # noqa: E712
            role.requires_mfa = False
        bootstrap_store.mark_setup_complete()
        print(f"Organization: {ORG_CODE}")
        print(f"Admin username: {ADMIN_USER}")
        print(f"Admin password: {ADMIN_PASS}")

    print("Local database recreation complete.")


if __name__ == "__main__":
    main()
