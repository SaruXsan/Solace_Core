# Security Route Permission Matrix

Foundation API (`/api/v1`). Auth: **Bearer JWT** unless noted.

| Method | Path | Purpose | Required permission(s) | Admin-only | Tenant-scoped | Audit |
|--------|------|---------|------------------------|------------|---------------|-------|
| GET | `/health` | Health / setup status | None (public) | No | No | No |
| GET | `/setup/status` | First-run status | None (public) | No | No | No |
| POST | `/setup/test-database` | Test SQL connection | None (setup) | No | No | No |
| POST | `/setup/save-database` | Save DB config | None (setup) | No | No | No |
| POST | `/setup/run-migrations` | Run Alembic | None (setup) | No | No | No |
| POST | `/setup/complete` | Create org + admin | None (setup) | No | No | Yes (`setup.first_run_complete`) |
| POST | `/auth/login` | Authenticate | None (public) | No | No | Yes (`Audit_LoginEvents`) |
| POST | `/auth/logout` | Revoke session | Authenticated | No | No | No |
| GET | `/auth/me` | Current user + permissions | Authenticated | No | No | No |
| GET | `/dashboard/stats` | Dashboard metrics | `dashboard.read` | No | Yes (org context) | No |
| GET | `/users/structure` | Org/role structure | `users.read` or create/update | No | Yes | No |
| GET | `/users` | List users | `users.read` | No | Yes | No |
| GET | `/users/{id}` | Get user | `users.read` | No | Yes (same org) | No |
| POST | `/users` | Create user | `users.create` | No | Yes | Yes (`user_created`) |
| PATCH | `/users/{id}` | Update user | `users.update` | No | Yes | Yes (`user_updated` / `user_disabled`) |
| GET | `/roles/permissions` | List all permissions | `permissions.manage` or `roles.update` | No | No | No |
| GET | `/roles` | List roles | `roles.read` | No | Yes | No |
| POST | `/roles` | Create role | `roles.create` | No | Yes | Yes (`role_created`) |
| PATCH | `/roles/{id}` | Update role | `roles.update` | No | Yes | Yes (`role_updated`, `Audit_PermissionChanges`) |
| GET | `/modules` | List modules | `modules.read` | No | No | No |
| PATCH | `/modules/{id}` | Enable/disable module | `modules.update` | No | No | Yes (`module_enabled` / `module_disabled`) |
| GET | `/settings/system` | System settings | `settings.read` | No | No | No |
| PUT | `/settings/system` | Update system settings | `settings.update` | No | No | Yes (`Audit_ConfigChanges`) |
| GET | `/settings/database` | DB status | `settings.read` | No | No | No |
| POST | `/settings/database/test` | Test DB | `settings.read` | No | No | No |
| GET | `/settings/security` | Security settings | `settings.read` | No | No | No |
| GET | `/settings/ldap` | LDAP settings (masked) | `ldap.read` | No | No | No |
| PUT | `/settings/ldap` | Save LDAP settings | `ldap.update` | No | No | Yes (`Audit_ConfigChanges`, `Audit_Trail`) |
| POST | `/settings/ldap/test-connection` | Test LDAP | `ldap.test` | No | No | Yes (`Audit_Trail`) |
| POST | `/settings/ldap/test-user-lookup` | Test LDAP user | `ldap.test` | No | No | Yes (`Audit_Trail`) |
| GET | `/settings/mfa` | MFA settings (masked SMTP) | `mfa.read` | No | No | No |
| PUT | `/settings/mfa` | Save MFA/SMTP | `mfa.update` | No | No | Yes (`Audit_ConfigChanges`) |
| GET | `/settings/ai-providers` | AI provider registry | `ai_providers.read` | No | No | No |
| PATCH | `/settings/ai-providers/{code}` | Enable provider | `ai_providers.update` | No | No | Yes (`Audit_ConfigChanges`) |
| GET | `/settings/redaction` | Redaction rules | `redaction.read` | No | No | No |
| POST | `/settings/redaction` | Add redaction rule | `settings.update` | No | No | Yes (`Audit_ConfigChanges`) |
| POST | `/mfa/challenges` | Create OTP challenge | `mfa.update` | No | No | Yes (`Audit_MFAEvents`) |
| POST | `/mfa/challenges/verify` | Verify OTP (login flow) | Authenticated / login | No | No | Yes (`Audit_MFAEvents`) |
| POST | `/mfa/challenges/resend` | Resend OTP | `mfa.update` | No | No | Yes (`Audit_MFAEvents`) |
| GET | `/organizations` | List orgs/branches/depts | `organizations.read` or related | No | Yes | No |
| POST | `/organizations/branches` | Create branch | `branches.update` | No | Yes | Yes (`branch_created`) |
| POST | `/organizations/departments` | Create department | `departments.update` | No | Yes | Yes (`department_created`) |
| GET | `/compliance/rfi/sections` | RFI Center | `compliance.read` | No | No | No |
| PUT | `/compliance/rfi/questions/{id}/answer` | Save RFI answer | `compliance.update` | No | No | No |
| GET | `/compliance/evidence` | Evidence library | `evidence.read` | No | No | No |
| POST | `/compliance/evidence/auto-linker/run` | Auto-linker | `compliance.update` | No | No | Yes (`evidence_auto_linker_run`) |
| POST | `/compliance/evidence/{id}/verify` | Verify evidence hash | `evidence.verify` | No | No | Yes (`evidence_hash_verified`) |
| GET | `/compliance/controls` | Control map | `compliance.read` | No | No | No |
| GET | `/compliance/incidents` | Incidents | `compliance.read` | No | No | No |
| GET | `/compliance/access-reviews` | Access reviews | `compliance.read` | No | No | No |
| GET | `/compliance/change-requests` | Change requests | `compliance.read` | No | No | No |
| POST | `/compliance/redaction/test` | Test redaction | `redaction.test` | No | No | No |
| GET | `/logs/*` | Audit / login / admin logs | `logs.read` / `audit.read` | No | No | No |
| GET | `/memory/atoms` | Memory atoms | `memory.read` | No | Yes (user scoped) | No |
| POST | `/memory/atoms` | Create memory atom | `memory.read` | No | Yes | No |
| GET | `/memory/personas` | Personas | `personas.read` | No | Yes | No |
| GET | `/memory/rem-proposals` | REM proposals | `rem.read` | No | Yes | No |
| GET | `/evidence/infra/*` | Infra evidence lists | `compliance.read` | No | No | No |
| GET | `/evidence/appsec/*` | AppSec evidence lists | `compliance.read` | No | No | No |

## Admin-only / bootstrap

`require_admin` (legacy `is_admin` flag) is retained only for emergency bootstrap paths if added later. Platform routes use **permission codes** above.

Users with `is_admin=true` receive effective permission `*` and retain full access (preserves existing admin login).

## Permission denied

Missing permission on authenticated request: **HTTP 403**, `Audit_Trail` event `security.permission_denied` (no sensitive payload).

Unauthenticated: **HTTP 401**.

## Default system roles

| Role code | Permissions |
|-----------|-------------|
| `system_administrator` | All foundation permissions |
| `standard_user` | `dashboard.read`, `memory.read`, `personas.read`, `rem.read` |
| `read_only` | All `*.read` + `redaction.test` |
| `compliance_reviewer` | Read-only compliance/audit + `compliance.update`, `evidence.verify` |
| `security_admin` | Security/settings/LDAP/MFA/logs + selected admin |
| `admin` (legacy) | Synced to all permissions if present |

Roles are upserted on application startup and during foundation seed.
