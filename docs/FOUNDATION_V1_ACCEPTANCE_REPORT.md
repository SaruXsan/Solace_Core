# Foundation V1 Acceptance Report

**Project:** Solace Enterprise Core  
**Checkpoint:** Foundation V1 Frozen  
**Date:** 2026-05-17  
**Status:** Accepted

---

## Summary

Foundation V1 passed all automated acceptance checks, backend unit tests, and frontend production build. The platform foundation is frozen for scope control; business modules remain placeholders.

| Gate | Result |
|------|--------|
| Acceptance script (`scripts/foundation_acceptance_check.py`) | **18/18 PASS** |
| Backend unit tests (`tests.test_rbac_tenant`) | **5/5 PASS** |
| Backend import (`app.main`) | **PASS** |
| Frontend build (`npm run build`) | **PASS** |

---

## Acceptance check — 18/18 PASS

Run with API on http://127.0.0.1:8080 and `SOLACE_MASTER_KEY` set:

```bat
call scripts\set_env.local.bat
backend\venv\Scripts\python.exe scripts\foundation_acceptance_check.py
```

| # | Check | Result | Detail |
|---|--------|--------|--------|
| 1 | SOLACE_MASTER_KEY present | PASS | length ≥ 32 |
| 2 | Backend health endpoint | PASS | HTTP 200 |
| 3 | Setup complete | PASS | `setup_complete=True` |
| 4 | Database configured (bootstrap) | PASS | `database_configured=True` |
| 5 | Alembic at head | PASS | `003_foundation_completion` |
| 6 | Database connectivity | PASS | `SELECT 1 OK` |
| 7 | Encrypted settings table | PASS | `Core_EncryptedSettings` |
| 8 | Core tables exist | PASS | all required tables present |
| 9 | Default permissions seeded | PASS | count=42 (≥35 foundation codes) |
| 10 | Default system roles exist | PASS | all 5 system roles |
| 11 | Admin user exists | PASS | `admin` |
| 12 | Placeholder modules registered | PASS | count=6 |
| 13 | Evidence `digital_signature_hash` column | PASS | present |
| 14 | RFI sections seeded | PASS | distinct_sections=7 |
| 15 | LDAP settings endpoint | PASS | HTTP 200 |
| 16 | MFA settings endpoint | PASS | HTTP 200 |
| 17 | Dashboard stats endpoint | PASS | HTTP 200 |
| 18 | `/auth/me` returns permissions | PASS | wildcard or permission list returned |

**Login note:** When admin MFA blocks HTTP login (OTP/cooldown), the acceptance script issues an acceptance session via `auth_service.create_session` to verify protected endpoints. Confirm interactive UI login separately, or set `SOLACE_ADMIN_MFA_OTP` for full HTTP login path validation.

---

## Backend test result

```bat
cd backend
set PYTHONPATH=%CD%
venv\Scripts\python.exe -m unittest tests.test_rbac_tenant -v
```

| Test | Result |
|------|--------|
| `test_admin_has_wildcard` | PASS |
| `test_missing_permission_raises_403` | PASS |
| `test_organization_context_roundtrip` | PASS |
| `test_system_bypass_is_explicit` | PASS |
| `test_require_organization_context_without_org` | PASS |

**Total: 5/5 PASS** (0.04s)

---

## Frontend build result

```bat
cd frontend
npm run build
```

| Step | Result |
|------|--------|
| `tsc -b` | PASS |
| `vite build` | PASS |

Production assets emitted to `frontend/dist/` (gitignored; rebuild after clone).

---

## Known limitations

- **Business modules** — Document Hub, HR, Legal, Operations, IT/Network, Email Intelligence are registry placeholders only; no domain workflows.
- **Admin MFA** — Automated acceptance may use session fallback when HTTP login is MFA-blocked; UI login requires OTP when MFA is enforced.
- **`is_admin=true`** — Bootstrap admin still receives wildcard `*` permissions; new users should use roles.
- **Route guard** — UI shows Access Denied for unauthorized routes; API independently returns 403.
- **RFI answer UI** — Not separately permission-gated beyond API enforcement.
- **Platform** — Windows + SQL Server + ODBC Driver 18 required; no SQLite fallback.
- **Secrets** — `SOLACE_MASTER_KEY` and `scripts/set_env.local.bat` are not in git; `bootstrap.enc` is local runtime state.

---

## Next recommended phase

**Phase 2 — Security & operations hardening**

1. Validate MFA/SMTP and LDAP directory login end-to-end in a staging environment.
2. Migrate operational users off `is_admin` wildcard to role-only RBAC.
3. Add SQL Server integration tests in CI.

**Phase 3 — First business module**

4. Implement **one** vertical slice (recommended: Document Hub) behind module enable flag, without expanding foundation scope.

---

## Related documents

- [FOUNDATION_V1_FREEZE.md](./FOUNDATION_V1_FREEZE.md) — scope, commands, freeze rules
- [SECURITY_ROUTE_PERMISSION_MATRIX.md](./SECURITY_ROUTE_PERMISSION_MATRIX.md) — API permission matrix
- [README.md](../README.md) — quick start and operations

---

## Git checkpoint

| Item | Value |
|------|--------|
| Commit message | `Freeze Solace Enterprise Core Foundation V1` |
| Annotated tag | `FOUNDATION_V1_FROZEN` |

See repository `git log` and `git tag -l` for commit hash after checkpoint creation.
