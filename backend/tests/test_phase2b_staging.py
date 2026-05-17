"""Phase 2B staging validation unit tests."""

from __future__ import annotations

import unittest
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from app.core.exceptions import SolaceHTTPException
from app.core.permissions import assert_any_permission, get_user_permission_codes
from app.models.platform import CoreLoginAttempt, CoreSession, CoreUser
from app.services import auth_service, ldap_diagnostics_service, platform_settings_service
from app.services import security_readiness_service, session_service
from app.services.setup_service import _friendly_sql_error, test_sql_connection


class LdapSafeResponseTests(unittest.TestCase):
    def test_certificate_error_is_safe(self) -> None:
        msg = ldap_diagnostics_service._safe_error(Exception("SSL certificate verify failed"))
        self.assertIn("TLS", msg)
        self.assertNotIn("password", msg.lower())

    def test_bind_error_is_safe(self) -> None:
        msg = ldap_diagnostics_service._safe_error(Exception("invalid credentials bind"))
        self.assertIn("Bind", msg)


class SmtpSafeResponseTests(unittest.TestCase):
    def test_auth_failure_message(self) -> None:
        msg = platform_settings_service._classify_smtp_error(Exception("535 authentication failed"))
        self.assertIn("authentication", msg.lower())
        self.assertNotIn("secret", msg.lower())

    def test_tls_failure_message(self) -> None:
        msg = platform_settings_service._classify_smtp_error(Exception("STARTTLS failed"))
        self.assertIn("TLS", msg)

    def test_port_blocked_message(self) -> None:
        msg = platform_settings_service._classify_smtp_error(Exception("Connection refused 10061"))
        self.assertIn("connect", msg.lower())


class SqlServerGuardTests(unittest.TestCase):
    def test_sqlite_rejected(self) -> None:
        from app.core.database import init_engine

        with self.assertRaises(RuntimeError) as ctx:
            init_engine("sqlite:///./x.db")
        self.assertIn("SQLite", str(ctx.exception))

    def test_non_mssql_rejected(self) -> None:
        from app.core.database import init_engine

        with self.assertRaises(RuntimeError) as ctx:
            init_engine("postgresql://localhost/db")
        self.assertIn("SQL Server", str(ctx.exception))

    def test_invalid_url_friendly_message(self) -> None:
        result = test_sql_connection("postgres://localhost/db")
        self.assertFalse(result["success"])
        self.assertIn("SQL Server", result["message"])

    def test_odbc_driver_hint(self) -> None:
        msg = _friendly_sql_error(Exception("ODBC Driver 18 for SQL Server not found"))
        self.assertIn("ODBC", msg)


class LockoutAlignmentTests(unittest.TestCase):
    def test_directory_only_user_skips_local_lockout(self) -> None:
        db = MagicMock()
        user = CoreUser(
            id=uuid.uuid4(),
            is_directory_user=True,
            password_hash=None,
            failed_login_count=0,
        )
        auth_service._apply_local_lockout(db, user, "127.0.0.1")
        self.assertEqual(user.failed_login_count, 0)

    def test_local_user_increments_lockout_counter(self) -> None:
        db = MagicMock()
        user = CoreUser(
            id=uuid.uuid4(),
            is_directory_user=False,
            password_hash="x",
            failed_login_count=0,
        )
        with patch.object(auth_service.settings, "login_max_attempts", 99):
            auth_service._apply_local_lockout(db, user, None)
        self.assertEqual(user.failed_login_count, 1)


class SessionRevokeTests(unittest.TestCase):
    def test_revoke_current_sets_revoked_at(self) -> None:
        db = MagicMock()
        sess = CoreSession(id=uuid.uuid4(), token_jti="jti-1", user_id=uuid.uuid4())
        db.scalar.return_value = sess
        session_service.revoke_current_session(db, "jti-1", sess.user_id)
        self.assertIsNotNone(sess.revoked_at)

    def test_revoke_other_skips_current_jti(self) -> None:
        db = MagicMock()
        current = CoreSession(id=uuid.uuid4(), token_jti="keep", user_id=uuid.uuid4())
        other = CoreSession(id=uuid.uuid4(), token_jti="drop", user_id=current.user_id)
        db.scalars.return_value.all.return_value = [current, other]
        count = session_service.revoke_other_sessions(
            db, current.user_id, uuid.uuid4(), "keep"
        )
        self.assertEqual(count, 1)
        self.assertIsNotNone(other.revoked_at)
        self.assertIsNone(current.revoked_at)


class LoginAttemptFilterTests(unittest.TestCase):
    def test_filters_by_auth_source(self) -> None:
        from app.services.login_attempt_service import list_login_attempts

        db = MagicMock()
        row = CoreLoginAttempt(
            id=uuid.uuid4(),
            username="alice",
            success=False,
            auth_source="LDAP",
            failure_reason="bad_password",
            created_at=datetime.now(timezone.utc),
        )
        db.scalars.return_value.all.return_value = [row]
        out = list_login_attempts(db, auth_source="LDAP")
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["auth_source"], "LDAP")


class BreakGlassTests(unittest.TestCase):
    def test_break_glass_user_detected(self) -> None:
        db = MagicMock()
        admin = CoreUser(
            id=uuid.uuid4(),
            username="breakglass",
            is_admin=True,
            display_name="BG",
            email="bg@test",
            deleted_at=None,
        )
        db.scalars.return_value.all.return_value = [admin]
        db.scalar.return_value = 0
        with patch(
            "app.services.security_readiness_service.get_user_permission_codes",
            return_value={"*"},
        ):
            users = security_readiness_service.get_break_glass_users(db)
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0]["username"], "breakglass")


class PermissionDeniedAuditTests(unittest.TestCase):
    def test_denied_logs_and_raises(self) -> None:
        db = MagicMock()
        db.scalars.return_value.all.return_value = []
        user = CoreUser(id=uuid.uuid4(), is_admin=False, organization_id=uuid.uuid4())
        with patch("app.services.audit_service.log_permission_denied") as log_denied:
            with self.assertRaises(SolaceHTTPException) as ctx:
                assert_any_permission(db, user, "security.readiness", ip_address="10.0.0.1")
            self.assertEqual(ctx.exception.status_code, 403)
            log_denied.assert_called_once()


class AdminWithRolesNoWildcardTests(unittest.TestCase):
    def test_admin_with_roles_no_wildcard(self) -> None:
        db = MagicMock()
        user = CoreUser(id=uuid.uuid4(), is_admin=True, organization_id=uuid.uuid4())

        def scalars_side_effect(stmt):
            result = MagicMock()
            if "Core_UserRole" in str(stmt):
                result.all.return_value = [uuid.uuid4()]
            elif "Core_RolePermission" in str(stmt):
                result.all.return_value = [uuid.uuid4()]
            elif "Core_Permission" in str(stmt):
                result.all.return_value = ["security.readiness"]
            else:
                result.all.return_value = []
            return result

        db.scalars.side_effect = scalars_side_effect
        codes = get_user_permission_codes(db, user)
        self.assertNotIn("*", codes)
        self.assertIn("security.readiness", codes)


if __name__ == "__main__":
    unittest.main()
