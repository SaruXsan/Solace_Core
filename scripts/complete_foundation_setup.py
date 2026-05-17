"""Complete first-run setup: bootstrap, migrations, seed, admin user."""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.core.config import require_master_key
from app.core.database import init_engine, session_scope
from app.services import bootstrap_store, setup_service, seed_service
from app.services.auth_service import create_admin_user
from app.models.platform import CoreOrganization

require_master_key()

SERVER = os.environ.get("SOLACE_DB_SERVER", "localhost")
USER = os.environ.get("SOLACE_DB_USER", "cursor")
PASSWORD = os.environ.get("SOLACE_DB_PASSWORD", "")
DATABASE = os.environ.get("SOLACE_DB_NAME", "SolaceEnterpriseCore")

ADMIN_USER = os.environ.get("SOLACE_ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("SOLACE_ADMIN_PASSWORD", "SolaceAdmin2026!")
ADMIN_EMAIL = os.environ.get("SOLACE_ADMIN_EMAIL", "admin@local")
ORG_NAME = os.environ.get("SOLACE_ORG_NAME", "Default Organization")
ORG_CODE = os.environ.get("SOLACE_ORG_CODE", "DEFAULT")

if not PASSWORD:
    print("Set SOLACE_DB_PASSWORD")
    sys.exit(1)

if bootstrap_store.is_setup_complete():
    print("Setup already complete. Delete backend/data/bootstrap.enc to re-run.")
    sys.exit(0)

url = setup_service.build_mssql_url(SERVER, DATABASE, USER, PASSWORD, trust_cert=True)
test = setup_service.test_sql_connection(url)
if not test["success"]:
    print("Connection failed:", test["message"])
    sys.exit(1)

bootstrap_store.save_database_url(url)
init_engine(url)
print("Saved encrypted bootstrap connection")

result = subprocess.run(
    [
        sys.executable,
        "-m",
        "alembic",
        "-c",
        str(ROOT / "alembic.ini"),
        "upgrade",
        "head",
    ],
    cwd=str(ROOT),
    capture_output=True,
    text=True,
)
if result.returncode != 0:
    print("Migration failed:", result.stderr or result.stdout)
    sys.exit(1)
print("Migrations applied")

with session_scope() as db:
    org = CoreOrganization(name=ORG_NAME, code=ORG_CODE, is_active=True)
    db.add(org)
    db.flush()
    admin = create_admin_user(
        db, org.id, ADMIN_EMAIL, ADMIN_USER, ADMIN_PASS, "System Administrator"
    )
    seed_service.seed_foundation_data(db)
    bootstrap_store.mark_setup_complete()
    print(f"Organization: {ORG_CODE}")
    print(f"Admin username: {ADMIN_USER}")
    print(f"Admin password: {ADMIN_PASS}")
    print("Change the admin password after first login.")

print("Setup complete.")
