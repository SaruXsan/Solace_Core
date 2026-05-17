"""One-time: create SolaceEnterpriseCore database on local SQL Server."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from sqlalchemy import create_engine, text

from app.core.config import require_master_key
from app.services.setup_service import build_mssql_url, test_sql_connection

require_master_key()

SERVER = os.environ.get("SOLACE_DB_SERVER", "localhost")
USER = os.environ.get("SOLACE_DB_USER", "cursor")
PASSWORD = os.environ.get("SOLACE_DB_PASSWORD", "")
DATABASE = os.environ.get("SOLACE_DB_NAME", "SolaceEnterpriseCore")

if not PASSWORD:
    print("Set SOLACE_DB_PASSWORD or pass via env")
    sys.exit(1)

master_url = build_mssql_url(SERVER, "master", USER, PASSWORD, trust_cert=True)
engine = create_engine(master_url, isolation_level="AUTOCOMMIT")
with engine.connect() as conn:
    exists = conn.execute(
        text("SELECT name FROM sys.databases WHERE name = :db"), {"db": DATABASE}
    ).fetchone()
    if not exists:
        conn.execute(text(f"CREATE DATABASE [{DATABASE}]"))
        print(f"Created database [{DATABASE}]")
    else:
        print(f"Database [{DATABASE}] already exists")
engine.dispose()

app_url = build_mssql_url(SERVER, DATABASE, USER, PASSWORD, trust_cert=True)
result = test_sql_connection(app_url)
print(result)
sys.exit(0 if result.get("success") else 1)
