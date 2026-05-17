"""SQL Server integration tests — run only when SOLACE_TEST_SQL_URL is set."""

from __future__ import annotations

import os
import unittest

from app.core.database import init_engine
from app.services.setup_service import build_mssql_url, test_sql_connection


def _test_url() -> str | None:
    return os.environ.get("SOLACE_TEST_SQL_URL") or os.environ.get("SOLACE_DATABASE_URL")


@unittest.skipUnless(_test_url(), "Set SOLACE_TEST_SQL_URL for SQL Server integration tests")
class SqlServerIntegrationTests(unittest.TestCase):
    def test_connection_select_one(self) -> None:
        url = _test_url()
        assert url
        result = test_sql_connection(url)
        self.assertTrue(result["success"], result.get("message"))

    def test_init_engine_accepts_mssql(self) -> None:
        url = _test_url()
        assert url
        engine = init_engine(url)
        with engine.connect() as conn:
            from sqlalchemy import text

            row = conn.execute(text("SELECT 1")).scalar()
        self.assertEqual(row, 1)
        engine.dispose()


class SqlServerUrlBuilderTests(unittest.TestCase):
    def test_trusted_connection_url(self) -> None:
        url = build_mssql_url(
            server="localhost",
            database="SolaceTest",
            use_trusted_connection=True,
        )
        self.assertIn("mssql+pyodbc", url)
        self.assertIn("Trusted_Connection", url)

    def test_sql_auth_url(self) -> None:
        url = build_mssql_url(
            server="localhost",
            database="SolaceTest",
            username="sa",
            password="secret",
        )
        self.assertIn("mssql+pyodbc", url)
        self.assertIn("UID", url)


@unittest.skipUnless(
    os.environ.get("SOLACE_TEST_SQL_EMPTY_URL"),
    "Set SOLACE_TEST_SQL_EMPTY_URL to an empty database for migration test",
)
class SqlServerEmptyDbMigrationTests(unittest.TestCase):
    def test_empty_database_connects(self) -> None:
        url = os.environ["SOLACE_TEST_SQL_EMPTY_URL"]
        result = test_sql_connection(url)
        self.assertTrue(result["success"], result.get("message"))


if __name__ == "__main__":
    unittest.main()
