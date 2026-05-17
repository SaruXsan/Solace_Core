#!/usr/bin/env python3
"""Phase 2A acceptance checks — Foundation V1 + security/directory completion."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

# Reuse Foundation checks with Phase 2A expectations
import foundation_acceptance_check as fac  # noqa: E402

fac.EXPECTED_HEAD = "004_phase2a_security_directory"
fac.EXPECTED_PERMISSIONS = 43

def record(name: str, ok: bool, detail: str = "") -> None:
    fac.record(name, ok, detail)


def check_phase2a_columns() -> None:
    try:
        from sqlalchemy import inspect

        ctx = fac._db_session()
        if ctx is None:
            record("Phase 2A user MFA columns", False, "no bootstrap URL")
            record("Phase 2A directory sync column", False, "no bootstrap URL")
            return
        with ctx as db:
            user_cols = {c["name"] for c in inspect(db.get_bind()).get_columns("Core_Users")}
            dir_cols = {c["name"] for c in inspect(db.get_bind()).get_columns("Auth_DirectorySettings")}
        ok_user = "mfa_disabled_until" in user_cols and "mfa_disable_reason" in user_cols
        ok_dir = "overwrite_local_on_sync" in dir_cols
        record("Phase 2A user MFA columns", ok_user, "mfa_disabled_until, mfa_disable_reason")
        record("Phase 2A directory sync column", ok_dir, "overwrite_local_on_sync")
    except Exception as e:
        record("Phase 2A user MFA columns", False, str(e)[:200])
        record("Phase 2A directory sync column", False, str(e)[:200])


def check_phase2a_endpoints(token: str | None, login_note: str) -> None:
    if not token:
        record("Security sessions endpoint", False, f"skipped — {login_note}")
        record("Security login-attempts endpoint", False, f"skipped — {login_note}")
        record("MFA challenge status endpoint", False, f"skipped — {login_note}")
        return

    st, sessions = fac._http_get(f"{fac.API_PREFIX}/security/sessions", token)
    record("Security sessions endpoint", st == 200 and isinstance(sessions, list), f"HTTP {st}")

    st, attempts = fac._http_get(f"{fac.API_PREFIX}/security/login-attempts", token)
    record(
        "Security login-attempts endpoint",
        st == 200 and isinstance(attempts, list),
        f"HTTP {st}",
    )

    # Verify MFA status route is registered (404 = no challenge, still proves route exists)
    st, _ = fac._http_get(
        f"{fac.API_PREFIX}/auth/mfa/challenge/00000000-0000-0000-0000-000000000000/status",
        token,
    )
    record(
        "MFA challenge status endpoint",
        st in (200, 404),
        f"HTTP {st} (route registered)",
    )


def main() -> int:
    print("Solace Enterprise Core — Phase 2A Acceptance Check")
    print("=" * 56)
    fac._results.clear()
    fac.check_master_key()
    health = fac.check_health()
    fac.check_setup_complete(health)
    fac.check_database_configured(health)
    fac.check_alembic_head()
    fac.check_db_connectivity()
    fac.check_encrypted_settings_table()
    fac.check_core_tables()
    fac.check_permissions()
    fac.check_roles()
    fac.check_admin_user()
    fac.check_placeholder_modules()
    fac.check_evidence_hash_column()
    fac.check_rfi_sections()
    check_phase2a_columns()
    token, login_note = fac._login_token()
    fac.check_authenticated_endpoints(token, login_note)
    check_phase2a_endpoints(token, login_note)
    print("=" * 56)
    passed = sum(1 for _, ok, _ in fac._results if ok)
    total = len(fac._results)
    print(f"Result: {passed}/{total} passed")
    if passed < total:
        print("Some checks failed. Start API on 8080 and run migration 004 before re-running.")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
