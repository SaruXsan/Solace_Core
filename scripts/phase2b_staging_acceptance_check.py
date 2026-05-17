#!/usr/bin/env python3
"""Phase 2B staging acceptance — SQL Server, security endpoints, audit readiness."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

import foundation_acceptance_check as fac  # noqa: E402
import phase2a_acceptance_check as p2a  # noqa: E402

fac.EXPECTED_HEAD = os.environ.get("SOLACE_ACCEPTANCE_HEAD", "005_phase2c_enterprise_scope")
fac.EXPECTED_PERMISSIONS = 52
p2a.fac.EXPECTED_HEAD = fac.EXPECTED_HEAD
p2a.fac.EXPECTED_PERMISSIONS = 44


def check_encrypted_settings_roundtrip() -> None:
    try:
        from app.services import settings_service

        ctx = fac._db_session()
        if ctx is None:
            p2a.record("Encrypted settings read/write", False, "no bootstrap URL")
            return
        with ctx as db:
            settings_service.set_encrypted_setting(
                db, "_acceptance_probe", "probe-value", category="test"
            )
            val = settings_service.get_encrypted_setting(db, "_acceptance_probe")
            masked = settings_service.get_encrypted_masked(db, "_acceptance_probe")
            db.commit()
        ok = val == "probe-value" and masked is not None and "****" in masked
        p2a.record("Encrypted settings read/write", ok, "roundtrip OK" if ok else "mismatch")
    except Exception as e:
        p2a.record("Encrypted settings read/write", False, str(e)[:200])


def check_staging_security_api(token: str | None, login_note: str) -> None:
    if not token:
        for name in (
            "Security readiness endpoint",
            "Security sessions endpoint",
            "Security login-attempts endpoint",
            "Audit trail reachable",
            "Permission denied audit query",
        ):
            p2a.record(name, False, f"skipped — {login_note}")
        return

    st, ready = fac._http_get(f"{fac.API_PREFIX}/security/readiness", token)
    ok = st == 200 and isinstance(ready, dict) and "locked_users_count" in ready
    p2a.record("Security readiness endpoint", ok, f"HTTP {st}")

    st, sessions = fac._http_get(f"{fac.API_PREFIX}/security/sessions", token)
    p2a.record("Security sessions endpoint", st == 200 and isinstance(sessions, list), f"HTTP {st}")

    st, attempts = fac._http_get(f"{fac.API_PREFIX}/security/login-attempts", token)
    p2a.record(
        "Security login-attempts endpoint",
        st == 200 and isinstance(attempts, list),
        f"HTTP {st}",
    )

    st, audit = fac._http_get(f"{fac.API_PREFIX}/logs/audit-trail?limit=5", token)
    p2a.record("Audit trail reachable", st == 200, f"HTTP {st}")

    st, _ = fac._http_get(
        f"{fac.API_PREFIX}/logs/audit-trail?limit=20&event_type=security", token
    )
    p2a.record("Permission denied audit query", st == 200, f"HTTP {st}")

    st, ldap_diag = fac._http_post(
        f"{fac.API_PREFIX}/security/ldap/diagnostics",
        {},
        token=token,
    )
    p2a.record(
        "LDAP diagnostics endpoint",
        st in (200, 400),
        f"HTTP {st}",
    )


def check_sql_server_only() -> None:
    try:
        from app.core.database import init_engine

        try:
            init_engine("sqlite:///./test.db")
            p2a.record("SQLite fallback blocked", False, "sqlite accepted")
        except RuntimeError as e:
            p2a.record("SQLite fallback blocked", True, str(e)[:80])
    except Exception as e:
        p2a.record("SQLite fallback blocked", False, str(e)[:200])


def main() -> int:
    print("Solace Enterprise Core — Phase 2B Staging Acceptance Check")
    print("=" * 56)
    fac._results.clear()
    fac.check_master_key()
    health = fac.check_health()
    fac.check_setup_complete(health)
    fac.check_database_configured(health)
    fac.check_alembic_head()
    fac.check_db_connectivity()
    check_sql_server_only()
    check_encrypted_settings_roundtrip()
    fac.check_encrypted_settings_table()
    fac.check_core_tables()
    fac.check_permissions()
    fac.check_roles()
    fac.check_admin_user()
    fac.check_placeholder_modules()
    fac.check_evidence_hash_column()
    fac.check_rfi_sections()
    p2a.check_phase2a_columns()
    token, login_note = fac._login_token()
    fac.check_authenticated_endpoints(token, login_note)
    p2a.check_phase2a_endpoints(token, login_note)
    check_staging_security_api(token, login_note)
    print("=" * 56)
    passed = sum(1 for _, ok, _ in fac._results if ok)
    total = len(fac._results)
    print(f"Result: {passed}/{total} passed")
    if passed < total:
        print("Restart API after deploy; verify SQL Server and SOLACE_MASTER_KEY.")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
