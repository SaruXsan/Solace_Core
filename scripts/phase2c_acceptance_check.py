#!/usr/bin/env python3
"""Phase 2C operational scope acceptance — extends Phase 2B staging checks."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

import foundation_acceptance_check as fac  # noqa: E402
import phase2a_acceptance_check as p2a  # noqa: E402
import phase2b_staging_acceptance_check as p2b  # noqa: E402

fac.EXPECTED_HEAD = os.environ.get("SOLACE_ACCEPTANCE_HEAD", "005_phase2c_enterprise_scope")
fac.EXPECTED_PERMISSIONS = 52
p2a.fac.EXPECTED_HEAD = fac.EXPECTED_HEAD
p2a.fac.EXPECTED_PERMISSIONS = 52
p2b.fac.EXPECTED_HEAD = fac.EXPECTED_HEAD
p2b.fac.EXPECTED_PERMISSIONS = 52

DEV_SESSION_USER_AGENT = "phase2c-acceptance-check-dev"
DEV_FALLBACK_BANNER = (
    "Using dev acceptance session fallback because SMTP/MFA OTP is not configured."
)
SMTP_POSTPONED_NOTE = (
    "SMTP / real email OTP delivery validation is postponed (SMTP not configured). "
    "Phase 2C validates scope hierarchy, operational isolation, active scope, "
    "user scopes, scoped roles, and company-level separation — not email delivery."
)


def record(name: str, ok: bool, detail: str = "") -> None:
    fac.record(name, ok, detail)


def _dev_acceptance_fallback_allowed() -> bool:
    """Dev session fallback is only for local acceptance script runs."""
    if __name__ != "__main__" and os.environ.get("SOLACE_ACCEPTANCE_SCRIPT") != "1":
        return False
    flag = os.environ.get("SOLACE_ACCEPTANCE_ALLOW_DEV_SESSION", "1").strip().lower()
    return flag in ("1", "true", "yes")


def _create_dev_acceptance_session(username: str) -> str | None:
    """Issue a real JWT via auth_service.create_session (acceptance scripts only)."""
    if not _dev_acceptance_fallback_allowed():
        return None
    try:
        from sqlalchemy import select

        from app.models.platform import CoreUser
        from app.services import auth_service

        ctx = fac._db_session()
        if ctx is None:
            return None
        with ctx as db:
            user = db.scalar(
                select(CoreUser).where(
                    CoreUser.username == username,
                    CoreUser.deleted_at.is_(None),
                )
            )
            if user is None:
                return None
            fac._ensure_rbac_seeded(db)
            token, _session = auth_service.create_session(
                db, user, "127.0.0.1", DEV_SESSION_USER_AGENT
            )
            db.commit()
            return token
    except Exception:
        return None


def login_token_for_phase2c() -> tuple[str | None, str, bool]:
    """Try HTTP login, then dev acceptance session when MFA blocks and OTP is absent."""
    user = os.environ.get("SOLACE_ADMIN_USER", "admin")
    password = os.environ.get("SOLACE_ADMIN_PASSWORD", "SolaceAdmin2026!")
    status, data = fac._http_post(
        f"{fac.API_PREFIX}/auth/login",
        {"username": user, "password": password},
    )
    if status == 200 and isinstance(data, dict):
        if data.get("access_token"):
            return data["access_token"], "HTTP login", False
        if data.get("mfa_required"):
            otp = os.environ.get("SOLACE_ADMIN_MFA_OTP", "").strip()
            if otp:
                status2, data2 = fac._http_post(
                    f"{fac.API_PREFIX}/auth/login",
                    {"username": user, "password": password, "mfa_otp": otp},
                )
                if status2 == 200 and isinstance(data2, dict) and data2.get("access_token"):
                    return data2["access_token"], "HTTP login + MFA OTP", False
            token = _create_dev_acceptance_session(user)
            if token:
                print(DEV_FALLBACK_BANNER)
                return (
                    token,
                    "dev acceptance session (operational scope checks; SMTP/MFA OTP not validated)",
                    True,
                )
    return (
        None,
        "login failed — set SOLACE_ADMIN_USER/PASSWORD, SOLACE_ADMIN_MFA_OTP, or enable dev fallback",
        False,
    )


def check_phase2c_schema() -> None:
    try:
        from sqlalchemy import inspect

        ctx = fac._db_session()
        if ctx is None:
            record("Core_Countries table", False, "no bootstrap URL")
            record("Core_UserScopes table", False, "no bootstrap URL")
            return
        with ctx as db:
            bind = db.get_bind()
            tables = inspect(bind).get_table_names()
            ok_countries = "Core_Countries" in tables
            ok_scopes = "Core_UserScopes" in tables
            org_cols = {c["name"] for c in inspect(bind).get_columns("Core_Organizations")}
            ok_org_country = "country_id" in org_cols
            session_cols = {c["name"] for c in inspect(bind).get_columns("Core_Sessions")}
            ok_session_scope = "active_scope_type" in session_cols
        record("Core_Countries table", ok_countries, "")
        record("Core_UserScopes table", ok_scopes, "")
        record("Core_Organizations.country_id", ok_org_country, "")
        record("Core_Sessions active scope columns", ok_session_scope, "")
    except Exception as e:
        record("Core_Countries table", False, str(e)[:200])
        record("Core_UserScopes table", False, str(e)[:200])


def check_phase2c_api(token: str | None, login_note: str) -> None:
    if not token:
        for name in (
            "Countries endpoint",
            "Companies endpoint",
            "Auth available-scopes",
        ):
            record(name, False, f"skipped — {login_note}")
        return

    st, countries = fac._http_get(f"{fac.API_PREFIX}/countries", token)
    record("Countries endpoint", st == 200 and isinstance(countries, list), f"HTTP {st}")

    st, companies = fac._http_get(f"{fac.API_PREFIX}/organizations/companies", token)
    record("Companies endpoint", st == 200 and isinstance(companies, list), f"HTTP {st}")

    st, scopes = fac._http_get(f"{fac.API_PREFIX}/auth/available-scopes", token)
    record(
        "Auth available-scopes",
        st == 200 and isinstance(scopes, list),
        f"HTTP {st}, count={len(scopes) if isinstance(scopes, list) else 0}",
    )

    st, me = fac._http_get(f"{fac.API_PREFIX}/auth/me", token)
    ok_me = (
        st == 200
        and isinstance(me, dict)
        and "active_scope" in me
        and "available_scopes" in me
    )
    record("Auth me includes scope context", ok_me, f"HTTP {st}")


def main() -> int:
    os.environ.setdefault("SOLACE_ACCEPTANCE_SCRIPT", "1")
    print("Solace Enterprise Core — Phase 2C Operational Scope Acceptance")
    print("=" * 58)
    fac._results.clear()
    p2b.check_sql_server_only()
    fac.check_master_key()
    health = fac.check_health()
    fac.check_setup_complete(health)
    fac.check_database_configured(health)
    fac.check_alembic_head()
    fac.check_db_connectivity()
    p2b.check_encrypted_settings_roundtrip()
    fac.check_encrypted_settings_table()
    fac.check_core_tables()
    fac.check_permissions()
    fac.check_roles()
    fac.check_admin_user()
    fac.check_placeholder_modules()
    fac.check_evidence_hash_column()
    fac.check_rfi_sections()
    p2a.check_phase2a_columns()
    check_phase2c_schema()
    token, login_note, used_dev_fallback = login_token_for_phase2c()
    if used_dev_fallback:
        print(SMTP_POSTPONED_NOTE)
    fac.check_authenticated_endpoints(token, login_note)
    p2a.check_phase2a_endpoints(token, login_note)
    p2b.check_staging_security_api(token, login_note)
    check_phase2c_api(token, login_note)
    print("=" * 58)
    passed = sum(1 for _, ok, _ in fac._results if ok)
    total = len(fac._results)
    print(f"Result: {passed}/{total} passed")
    if used_dev_fallback:
        print(SMTP_POSTPONED_NOTE)
    elif passed < total:
        print("Restart API after deploy; verify migration 005 applied.")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
