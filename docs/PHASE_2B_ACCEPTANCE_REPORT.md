# Phase 2B Acceptance Report

**Project:** Solace Enterprise Core  
**Checkpoint:** Phase 2B Staging Validation & Security Hardening Complete  
**Date:** 2026-05-17  
**Status:** Accepted  
**Prior checkpoint:** Phase 2A (`PHASE_2A_SECURITY_DIRECTORY_COMPLETE` @ `d69494b`)

---

## Summary

Phase 2B hardens staging validation for SQL Server, SMTP/MFA failures, LDAP/LDAPS diagnostics, session and lockout alignment, break-glass policy, and a Security Readiness report — without adding business modules.

| Gate | Result |
|------|--------|
| Phase 2B acceptance (`scripts/phase2b_staging_acceptance_check.py`) | **31/31 PASS** |
| Backend health | **PASS** |
| Alembic head | **`004_phase2a_security_directory`** |
| Backend tests | **30 passed**, 3 skipped |
| Frontend build (`npm run build`) | **PASS** |
| Security routes on active backend | **Verified** |

---

## Scope delivered

| # | Area | Status |
|---|------|--------|
| 1 | Foundation acceptance updated for head `004` + Phase 2B staging script | Complete |
| 2 | SQL Server guards (no SQLite), friendly ODBC/SQL errors, integration test mode | Complete |
| 3 | SMTP safe failure classification + audit (no secret leak) | Complete |
| 4 | LDAP diagnostics endpoint + safe admin-readable errors | Complete |
| 5 | Lockout alignment (LDAP failures logged; local lockout scope; MFA does not lock directory) | Complete |
| 6 | Session expiry/revoke validation; revoke current / revoke others | Complete |
| 7 | Break-glass policy (readiness list, Users UI warning) | Complete |
| 8 | Security Readiness page + API (`security.readiness`) | Complete |
| 9 | Unit tests (`test_phase2b_staging`, `test_sql_server_integration`) | Complete |
| 10 | Documentation (`PHASE_2B_STAGING_HARDENING.md`) | Complete |

---

## Migration

No new migration in Phase 2B. Database remains at:

| Revision | Notes |
|----------|--------|
| `004_phase2a_security_directory` | Current head (Phase 2A schema) |

```bat
call scripts\set_env.local.bat
backend\venv\Scripts\python.exe -m alembic -c alembic.ini current
```

---

## New permission

| Code | Purpose |
|------|---------|
| `security.readiness` | View Security Readiness report and break-glass list |

---

## Acceptance commands

```bat
call scripts\set_env.local.bat
START_SOLACE.bat
backend\venv\Scripts\python.exe scripts\phase2b_staging_acceptance_check.py
```

Restart the API after deploying backend changes before running acceptance.

---

## Unit tests

```bat
cd backend
set PYTHONPATH=%CD%
venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
```

| Suite | Result |
|-------|--------|
| All discovered tests | **30 passed**, **3 skipped** |
| `tests.test_phase2b_staging` | 20 tests PASS |
| `tests.test_sql_server_integration` | 2 PASS, 3 skipped (no `SOLACE_TEST_SQL_URL`) |
| `tests.test_phase2a_security` | 3 PASS |
| `tests.test_rbac_tenant` | 5 PASS |

---

## Acceptance check detail (31/31)

| Check | Result |
|-------|--------|
| SOLACE_MASTER_KEY present | PASS |
| Backend health endpoint | PASS |
| Setup complete | PASS |
| Database configured (bootstrap) | PASS |
| Alembic at head `004_phase2a_security_directory` | PASS |
| Database connectivity | PASS |
| SQLite fallback blocked | PASS |
| Encrypted settings read/write | PASS |
| Encrypted settings table | PASS |
| Core tables exist | PASS |
| Default permissions seeded | PASS |
| Default system roles exist | PASS |
| Admin user exists | PASS |
| Placeholder modules registered | PASS |
| Evidence digital_signature_hash column | PASS |
| RFI sections seeded | PASS |
| Phase 2A user MFA columns | PASS |
| Phase 2A directory sync column | PASS |
| LDAP settings endpoint | PASS |
| MFA settings endpoint | PASS |
| Dashboard stats endpoint | PASS |
| `/auth/me` returns permissions | PASS |
| Security sessions endpoint | PASS |
| Security login-attempts endpoint | PASS |
| MFA challenge status endpoint | PASS |
| Security readiness endpoint | PASS |
| Audit trail reachable | PASS |
| Permission denied audit query | PASS |
| LDAP diagnostics endpoint | PASS |

Security routes verified on a restarted API process with Phase 2B code loaded.

---

## Git checkpoint

| Item | Value |
|------|--------|
| Commit message | `Complete Phase 2B staging validation and security hardening` |
| Annotated tag | `PHASE_2B_STAGING_HARDENING_COMPLETE` |

---

## Known limitations

- SQL Server empty-database migration integration test requires `SOLACE_TEST_SQL_EMPTY_URL` and manual `alembic upgrade head`.
- MFA end-to-end login in UI requires real SMTP in staging (automated acceptance uses session fallback when MFA blocks HTTP login).
- Session list shows active (non-expired, non-revoked) sessions only.
- Stale API process on port 8080 returned 404 for security routes until restart; always restart after deploy.

---

## Related documents

- [PHASE_2B_STAGING_HARDENING.md](./PHASE_2B_STAGING_HARDENING.md)
- [PHASE_2A_ACCEPTANCE_REPORT.md](./PHASE_2A_ACCEPTANCE_REPORT.md)
- [FOUNDATION_V1_FREEZE.md](./FOUNDATION_V1_FREEZE.md)
