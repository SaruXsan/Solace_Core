# Phase 2C Acceptance Report

**Project:** Solace Enterprise Core  
**Checkpoint:** Phase 2C Operational Scope & Isolation Complete  
**Date:** 2026-05-17  
**Status:** Accepted  
**Prior checkpoint:** Phase 2B (`PHASE_2B_STAGING_HARDENING_COMPLETE` @ `5019a01`)

---

## Summary

Phase 2C implements the **operational isolation lane** of the enterprise scope model: countries/jurisdictions, companies/legal entities, branches/sites, departments/business units, user scopes, scoped roles, session active operational scope, and company-level data separation. **Executive consolidation and business modules are out of scope.**

| Gate | Result |
|------|--------|
| Phase 2C acceptance (`scripts/phase2c_acceptance_check.py`) | **39/39 PASS** |
| Backend health | **PASS** |
| Alembic head | **`005_phase2c_enterprise_scope`** |
| Backend tests | **34 passed**, 3 skipped |
| Frontend build (`npm run build`) | **PASS** |
| Dev acceptance session fallback | **Used** (SMTP/MFA OTP not configured) |

---

## Scope of Phase 2C

| Area | Delivered |
|------|-----------|
| Countries / jurisdictions | `Core_Countries`, CRUD API, seed (LB, AE, SA) |
| Companies / legal entities | Extended `Core_Organizations` + `country_id`, companies API |
| Branches / sites | Extended `Core_Branches`, scoped list/create |
| Departments / business units | Extended `Core_Departments`, hierarchy fields |
| User scopes | `Core_UserScopes`, assignment API |
| Scoped roles | `Core_UserRoles` scope columns; permission resolution by active scope |
| Active operational scope | Session columns, JWT claims, `available-scopes`, `switch-scope` |
| Tenant isolation | Users, roles, dashboard, org structure filtered by **active company** |
| LDAP sync defaults | `default_sync_*` on `Auth_DirectorySettings` |
| Audit | `active_scope_switch` on scope change |
| UI | Top-bar scope selector; Countries, Companies, Branches, Departments, User Scopes pages |
| Tests | `test_phase2c_scope.py` |
| Acceptance | `phase2c_acceptance_check.py` (extends Phase 2B) |

**Not implemented (by design):**

- `Core_ConsolidationScopes` / executive consolidation lane
- Consolidation permissions, AI/reporting UI
- Specialized business modules (Document Hub, HR, Legal, etc.)

See [ENTERPRISE_SCOPE_MASTER_ARCHITECTURE.md](./ENTERPRISE_SCOPE_MASTER_ARCHITECTURE.md) for the future consolidation design.

---

## Migration

| Revision | Notes |
|----------|--------|
| `005_phase2c_enterprise_scope` | Current head |

```bat
backend\venv\Scripts\python.exe -m alembic -c alembic.ini upgrade head
backend\venv\Scripts\python.exe -m alembic -c alembic.ini current
```

### Tables added

| Table | Purpose |
|-------|---------|
| `Core_Countries` | Jurisdiction / regulatory context |
| `Core_UserScopes` | Operational scope grants per user |

### Tables extended

| Table | Changes |
|-------|---------|
| `Core_Organizations` | Company fields, `country_id` |
| `Core_Branches` | Site metadata, `country_id`, `is_active` |
| `Core_Departments` | `parent_department_id`, `manager_user_id`, `is_active` |
| `Core_Users` | `default_country_id`, `default_organization_id`, `default_branch_id`, `default_department_id` |
| `Core_UserRoles` | `scope_type`, country/org/branch/dept FKs |
| `Core_Sessions` | `active_scope_type`, `active_country_id`, `active_branch_id`, `active_department_id` |
| `Auth_DirectorySettings` | `default_sync_country_id`, `default_sync_organization_id`, `default_sync_branch_id`, `default_sync_department_id` |

---

## Endpoints added / extended

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v1/countries` | List countries |
| POST | `/api/v1/countries` | Create country |
| PATCH | `/api/v1/countries/{id}` | Update country |
| GET | `/api/v1/organizations/companies` | List companies (scoped) |
| POST | `/api/v1/organizations/companies` | Create company |
| PATCH | `/api/v1/organizations/companies/{id}` | Update company |
| GET/POST | `/api/v1/organizations/branches` | Branches (scoped) |
| GET/POST | `/api/v1/organizations/departments` | Departments (scoped) |
| GET | `/api/v1/scopes/users` | List user scope assignments |
| POST | `/api/v1/scopes/users` | Assign user scope |
| POST | `/api/v1/scopes/roles` | Assign scoped role |
| GET | `/api/v1/auth/available-scopes` | Scopes user may switch to |
| POST | `/api/v1/auth/switch-scope` | Change active scope + new JWT |
| GET | `/api/v1/auth/me` | Includes `active_scope`, `available_scopes` |

**Isolation:** `users`, `roles`, `dashboard` stats use **session active company**, not user home organization.

---

## UI pages added

| Route | Page |
|-------|------|
| `/platform/countries` | Countries / jurisdictions |
| `/platform/companies` | Companies / legal entities |
| `/platform/branches` | Branches / sites |
| `/platform/departments` | Departments / business units |
| `/platform/user-scopes` | User scope assignments |

**Component:** `ScopeSelector` in top bar (`Layout.tsx`).

---

## Permissions added

| Code | Purpose |
|------|---------|
| `countries.read` | View countries |
| `countries.manage` | Manage countries |
| `companies.read` | View companies |
| `companies.manage` | Manage companies |
| `scopes.read` | View enterprise scopes |
| `scopes.manage` | Manage scope definitions |
| `user_scopes.manage` | Assign user scopes |
| `role_scopes.manage` | Assign scoped roles |

Catalog size after seed: **58** permissions.

---

## Tests and build

```bat
cd backend
python -m unittest discover -s tests -p "test_*.py"

cd ..\frontend
npm run build
```

| Suite | Result |
|-------|--------|
| Backend unit tests | 34 passed, 3 skipped |
| Frontend production build | PASS |

Phase 2C tests (`test_phase2c_scope.py`): scope access, scoped roles, unauthorized switch (403), user list filtered by active org, system bypass token.

---

## Acceptance

```bat
call scripts\set_env.local.bat
set SOLACE_API_URL=http://127.0.0.1:8080
START_SOLACE.bat
python scripts\phase2c_acceptance_check.py
```

| Result | Detail |
|--------|--------|
| **39/39 PASS** | Includes Phase 2B staging checks + Phase 2C schema/API |

**Login note:** Dev acceptance session fallback was used because SMTP is not configured and `SOLACE_ADMIN_MFA_OTP` was not set. Production MFA behavior is unchanged. **SMTP / real email OTP validation** is postponed to staging/operations configuration.

---

## Known limitations

1. **Operational lane only** — no executive consolidation, roll-up reporting, or consolidation AI.
2. **No `scope_mode` on `Core_UserScopes`** — deferred to Phase 2D consolidation foundation.
3. **Branch/department scope** — modeled and switchable; most APIs filter at company level today.
4. **Global admin** — may switch to any company; lists reflect **active** company after switch.
5. **Cross-tenant DB integration tests** — env-gated; primary coverage is unit tests + acceptance HTTP.
6. **Interactive UI login** — requires SMTP + OTP when MFA enforced; verify separately from acceptance script.

---

## Next recommended phase

**Phase 2D — Executive Consolidation Foundation**

- `Core_ConsolidationScopes` (or extended scope model with `scope_mode`)
- Consolidation permissions (`consolidation.view`, `.report`, etc.)
- Explicit grants only; no implicit cross-company visibility
- Still **no** specialized business modules until operational + consolidation lanes are safe

See [ENTERPRISE_SCOPE_MASTER_ARCHITECTURE.md](./ENTERPRISE_SCOPE_MASTER_ARCHITECTURE.md).

---

## Tag

`PHASE_2C_OPERATIONAL_SCOPE_ISOLATION_COMPLETE`
