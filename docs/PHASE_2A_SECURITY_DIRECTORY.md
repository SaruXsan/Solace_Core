# Phase 2A — Security & Directory Completion

**Status:** Accepted and complete (2026-05-17)  
**Checkpoint tag:** `PHASE_2A_SECURITY_DIRECTORY_COMPLETE`  
**Acceptance report:** [PHASE_2A_ACCEPTANCE_REPORT.md](./PHASE_2A_ACCEPTANCE_REPORT.md)  
**Builds on:** Foundation V1 frozen (`FOUNDATION_V1_FROZEN`)

---

## Final completion report

| Gate | Result |
|------|--------|
| Migration `004_phase2a_security_directory` | Applied |
| `tests.test_rbac_tenant` | **5/5 PASS** |
| `tests.test_phase2a_security` | **3/3 PASS** |
| `npm run build` | **PASS** |
| Acceptance script | `scripts/phase2a_acceptance_check.py` |

Phase 2A delivers the operational authentication and directory layer. Business modules remain placeholders.

---

## Delivered capabilities

### Authentication & MFA
- Two-step login: password → OTP verification screen
- Public MFA endpoints: verify, resend, challenge status (no OTP in logs/UI)
- SMTP test email from MFA settings (`smtp.test`)
- MFA admin: reset cooldown, clear challenges, require privileged MFA, temporary disable with audited reason (`mfa.manage`)

### LDAP / directory
- Test bind and user lookup with username, email, display name, department, groups
- LDAPS certificate validation option; plain-LDAP production warning
- Group DN → Solace role mapping (table + UI)
- Preview roles for LDAP groups
- Sync preview (created / updated / unchanged / disabled — no writes)
- Sync apply with `is_directory_user`, `directory_source`, `directory_object_id`, `last_directory_sync_at`
- Preserves bootstrap admin; optional `overwrite_local_on_sync`

### Security operations
- Active sessions list; revoke one or all for user (`sessions.read` / `sessions.revoke`)
- Login attempts filter + 24h failed trends; admin unlock (`login_attempts.read`, `users.unlock`)

### RBAC
- `system_administrator` role assigned to all `is_admin` users on startup
- `is_admin` grants `*` **only** when admin has zero roles (break-glass)
- Normal admin access via `system_administrator` role permissions

---

## Migration

```bat
call scripts\set_env.local.bat
backend\venv\Scripts\python.exe -m alembic -c alembic.ini upgrade head
```

**Head:** `004_phase2a_security_directory`

| Table | New columns |
|-------|-------------|
| `Core_Users` | `mfa_disabled_until`, `mfa_disable_reason` |
| `Auth_DirectorySettings` | `overwrite_local_on_sync` |

---

## New API surface (summary)

| Prefix | Examples |
|--------|----------|
| `/auth/mfa/` | `verify`, `resend`, `challenge/{id}/status` |
| `/settings/mfa/` | `test-smtp` |
| `/settings/ldap/` | `group-mappings`, `preview-roles`, `sync/preview`, `sync/apply` |
| `/security/` | `sessions`, `login-attempts`, `users/unlock`, `users/{id}/mfa/*` |

---

## New permissions

`sessions.read`, `sessions.revoke`, `login_attempts.read`, `users.unlock`, `ldap.sync`, `mfa.manage`, `smtp.test`

---

## Run & verify

```bat
call scripts\set_env.local.bat
START_SOLACE.bat
backend\venv\Scripts\python.exe scripts\phase2a_acceptance_check.py
```

```bat
cd backend
set PYTHONPATH=%CD%
venv\Scripts\python.exe -m unittest tests.test_rbac_tenant tests.test_phase2a_security -v
cd ..\frontend
npm run build
```

---

## Emergency `is_admin`

Bootstrap users may keep `is_admin=true` for identification. Effective permissions come from assigned roles (typically `system_administrator`). Wildcard `*` applies only when an admin user has **no role assignments** — intentional break-glass for lockout recovery.

---

## Must not build yet

- Business module workflows (Document Hub, HR, Legal, etc.)
- Advanced Solace chat / REM intelligence
- Full LDAP delta sync scheduler / multi-OU automation

---

## Next recommended phase

**Phase 2B — Operations hardening:** SQL Server integration tests in CI, LDAP failure → lockout alignment, optimize directory sync performance, staging validation of SMTP/LDAP end-to-end.
