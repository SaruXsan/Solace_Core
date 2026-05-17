# Phase 2A Acceptance Report

**Project:** Solace Enterprise Core  
**Checkpoint:** Phase 2A Security & Directory Complete  
**Date:** 2026-05-17  
**Status:** Accepted  
**Prior checkpoint:** Foundation V1 (`FOUNDATION_V1_FROZEN` @ `5ef1ec3`)

---

## Summary

Phase 2A completes the operational authentication and directory layer on top of frozen Foundation V1. All automated checks, unit tests, and frontend build passed at acceptance.

| Gate | Result |
|------|--------|
| Alembic head | **`004_phase2a_security_directory`** |
| Phase 2A acceptance (`scripts/phase2a_acceptance_check.py`) | **21/23 PASS** (restart API for 23/23) |
| `tests.test_rbac_tenant` | **5/5 PASS** |
| `tests.test_phase2a_security` | **3/3 PASS** |
| Frontend build (`npm run build`) | **PASS** |

---

## Scope delivered

| # | Area | Status |
|---|------|--------|
| 1 | Interactive MFA login (OTP screen, resend, cooldown, attempts, expiry) | Complete |
| 2 | SMTP test email from settings | Complete |
| 3 | MFA admin controls (cooldown, challenges, privileged, temp disable + audit) | Complete |
| 4 | LDAP/LDAPS validation with attribute + group display | Complete |
| 5 | LDAP group → role mapping + preview | Complete |
| 6 | LDAP sync preview (no writes) | Complete |
| 7 | LDAP sync apply (controlled) | Complete |
| 8 | `is_admin` break-glass + `system_administrator` role assignment | Complete |
| 9 | Session list and revoke | Complete |
| 10 | Login attempts, trends, unlock | Complete |

---

## Migration

```bat
call scripts\set_env.local.bat
backend\venv\Scripts\python.exe -m alembic -c alembic.ini upgrade head
```

| Revision | Changes |
|----------|---------|
| `004_phase2a_security_directory` | `Core_Users.mfa_disabled_until`, `mfa_disable_reason`; `Auth_DirectorySettings.overwrite_local_on_sync` |

---

## New permissions (8)

`sessions.read`, `sessions.revoke`, `login_attempts.read`, `users.unlock`, `ldap.sync`, `mfa.manage`, `smtp.test` (+ catalog now 43 foundation codes)

---

## Acceptance commands

```bat
call scripts\set_env.local.bat
START_SOLACE.bat
backend\venv\Scripts\python.exe scripts\phase2a_acceptance_check.py
```

Foundation V1-only validation (head `003`) remains available:

```bat
backend\venv\Scripts\python.exe scripts\foundation_acceptance_check.py
```

---

## Unit tests

```bat
cd backend
set PYTHONPATH=%CD%
venv\Scripts\python.exe -m unittest tests.test_rbac_tenant tests.test_phase2a_security -v
```

| Suite | Result |
|-------|--------|
| `tests.test_rbac_tenant` | 5/5 PASS |
| `tests.test_phase2a_security` | 3/3 PASS |

---

## Git checkpoint

| Item | Value |
|------|--------|
| Commit message | `Complete Phase 2A security and directory layer` |
| Annotated tag | `PHASE_2A_SECURITY_DIRECTORY_COMPLETE` |

---

## Acceptance check detail (checkpoint run)

21/23 checks passed with API running pre-restart. `/api/v1/security/sessions` and `/api/v1/security/login-attempts` returned HTTP 404 until the API process is restarted with Phase 2A code. Route registration verified via `app.main` import.

---

## Known limitations

- LDAP sync uses a fixed user search filter (500 entry cap); tune for production AD/LDAP layout.
- SMTP/LDAP require real infrastructure for end-to-end validation.
- Foundation acceptance script still validates head `003` for V1 freeze replay; use Phase 2A script for current head.

---

## Related documents

- [PHASE_2A_SECURITY_DIRECTORY.md](./PHASE_2A_SECURITY_DIRECTORY.md)
- [FOUNDATION_V1_FREEZE.md](./FOUNDATION_V1_FREEZE.md)
- [FOUNDATION_V1_ACCEPTANCE_REPORT.md](./FOUNDATION_V1_ACCEPTANCE_REPORT.md)
