# Phase 2C — Enterprise Scope & Isolation Model (Operational Lane)

Foundation-only phase. **Operational isolation only** — see [ENTERPRISE_SCOPE_MASTER_ARCHITECTURE.md](./ENTERPRISE_SCOPE_MASTER_ARCHITECTURE.md) for the future executive consolidation lane (not implemented in migration 005).

No business modules (Document Hub, HR, Legal, etc.).

## Enterprise hierarchy

```
Holding / Enterprise Group
  └── Country / Jurisdiction     (Core_Countries)
        └── Company / Legal Entity (Core_Organizations — name retained)
              └── Branch / Site      (Core_Branches)
                    └── Department / Business Unit (Core_Departments)
```

| Level | Table | Purpose |
|-------|--------|---------|
| Country | `Core_Countries` | Legal/regulatory context (language, currency, timezone) |
| Company | `Core_Organizations` | **Primary tenant boundary** |
| Branch | `Core_Branches` | Operational / location boundary |
| Department | `Core_Departments` | Functional boundary |

## Country vs company

- **Country** does not isolate tenant data by itself.
- **Company / legal entity** (`Core_Organizations`) drives SQLAlchemy tenant context and query filters.
- Users may hold scopes at country, company, branch, or department level; active **company** is always set on the session for isolation.

## User scope model (`Core_UserScopes`)

- `scope_type`: `global` | `country` | `organization` | `branch` | `department`
- Nullable FKs pin the scope to hierarchy levels.
- `is_default` selects auto-login scope when only one applies.
- Bootstrap admins receive a **global** scope plus company scope via startup backfill.

## Scoped role model (`Core_UserRoles` extensions)

Role assignments include the same scope columns. Permissions resolve from roles whose scope matches (or is broader than) the **active scope**.

Example: `system_administrator` with `scope_type=global` applies everywhere; a `read_only` role on `organization_id=A` applies only when company A is active.

## Active scope selector

- `GET /api/v1/auth/available-scopes` — scopes the user may switch to
- `POST /api/v1/auth/switch-scope` — updates session + returns new JWT
- Top-bar selector in the UI (Country → Company → Branch → Department label)
- `GET /api/v1/auth/me` includes `active_scope` and `available_scopes`

## Tenant isolation rules

1. `set_organization_id()` / `require_active_organization_id()` use the **session active company**.
2. `user_service.list_users`, `dashboard_service`, and company/branch/department list APIs filter by active company unless `enable_system_bypass()` is active.
3. System bypass is explicit (`tenant_context.enable_system_bypass`) and must be audited when used in jobs.
4. Country-only scope does not replace company isolation — global users still pick an active company for queries.

## LDAP sync defaults

`Auth_DirectorySettings`:

- `default_sync_organization_id` (required for controlled import)
- `default_sync_country_id`, `default_sync_branch_id`, `default_sync_department_id` (optional)

New directory users are **not** global unless a global scope is explicitly assigned.

## Permissions added

`countries.read`, `countries.manage`, `companies.read`, `companies.manage`, `scopes.read`, `scopes.manage`, `user_scopes.manage`, `role_scopes.manage`

## Future modules

All modules must:

1. Attach data to `organization_id` (company).
2. Respect active scope from request context.
3. Never query tenant data without company context unless using audited system bypass.

## Migration

Head: `005_phase2c_enterprise_scope`

```bat
backend\venv\Scripts\python.exe -m alembic -c alembic.ini upgrade head
```

## Acceptance

Run from repo root with API on `SOLACE_API_URL` (default `http://127.0.0.1:8080`) and `SOLACE_MASTER_KEY` set:

```bat
python scripts\phase2c_acceptance_check.py
```

**Phase 2C acceptance does not require real SMTP.** When admin HTTP login returns `mfa_required` and `SOLACE_ADMIN_MFA_OTP` is not set, the script issues a **dev-only acceptance session** via `auth_service.create_session` (same JWT path as production login). This does not weaken production MFA, disable MFA globally, or expose OTP values.

**SMTP / MFA real email delivery** remains a staging/operations configuration task (configure SMTP, verify OTP in UI separately).

**Phase 2C validates:**

- Scope hierarchy (countries → companies → branches → departments)
- Operational isolation and company-level separation
- Active operational scope on session and JWT
- `Core_UserScopes` and scoped `Core_UserRoles`
- `available-scopes` / `switch-scope` / `/me` scope context
- Authenticated platform endpoints (not email delivery)

Disable the dev session fallback only if needed: `SOLACE_ACCEPTANCE_ALLOW_DEV_SESSION=0`.

---

## Final acceptance (checkpoint)

| Gate | Result |
|------|--------|
| Phase 2C acceptance (`scripts/phase2c_acceptance_check.py`) | **39/39 PASS** |
| Alembic head | **`005_phase2c_enterprise_scope`** |
| Backend tests | **34 passed**, 3 skipped |
| Frontend build | **PASS** |

**Login note:** Dev acceptance session fallback was used because SMTP/MFA OTP is not configured. Production MFA is unchanged. **SMTP / real OTP validation** is postponed to staging/operations configuration.

**Validated:** scope hierarchy, operational isolation, active scope, user scopes, scoped roles, company-level separation, authenticated platform endpoints.

**Not in Phase 2C:** executive consolidation (`Core_ConsolidationScopes`), consolidation UI/API, specialized business modules.

Full report: [PHASE_2C_ACCEPTANCE_REPORT.md](./PHASE_2C_ACCEPTANCE_REPORT.md)

**Tag:** `PHASE_2C_OPERATIONAL_SCOPE_ISOLATION_COMPLETE`
