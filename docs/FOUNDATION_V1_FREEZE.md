# Foundation V1 Freeze

**Status:** Frozen — accepted 2026-05-17.  
**Scope:** Platform foundation only — not business modules.  
**Checkpoint commit:** `5ef1ec3`  
**Checkpoint tag:** `FOUNDATION_V1_FROZEN`  
**Full report:** [FOUNDATION_V1_ACCEPTANCE_REPORT.md](./FOUNDATION_V1_ACCEPTANCE_REPORT.md)

## Final acceptance (frozen)

| Gate | Result |
|------|--------|
| `scripts/foundation_acceptance_check.py` | **18/18 PASS** |
| `tests.test_rbac_tenant` | **5/5 PASS** |
| `from app.main import app` | **PASS** |
| `npm run build` | **PASS** |

All acceptance checks passed with API running on port 8080. See the acceptance report for per-check detail and login/MFA notes.

## What Foundation V1 includes

- First-run setup (SQL Server, migrations, admin user) with setup gate
- `SOLACE_MASTER_KEY` enforcement and encrypted bootstrap / `Core_EncryptedSettings`
- Local auth, sessions, lockout, MFA email OTP foundation
- LDAP/LDAPS settings (canonical: `/api/v1/settings/ldap`)
- RBAC: 35 permissions, 5 system roles, route-level API enforcement
- Users, roles, organizations/branches/departments, modules registry
- Compliance: RFI Center (7 sections), evidence library with `digital_signature_hash`, control map, incidents, access reviews, change requests
- Audit/logs foundation tables and UI
- AI provider registry, memory/personas/REM tables (foundation only)
- Infra/AppSec evidence skeleton tables and list UI
- Tenant isolation session interceptor
- Dashboard metrics, acceptance check script

## Intentionally placeholder (do not implement in V1)

- **Business modules:** Document Hub, HR, Legal, Operations, IT/Network, Email Intelligence (registry only)
- Advanced Solace chat / REM intelligence
- Full LDAP user provisioning sync
- Per-table Infra/AppSec UI for every evidence type
- Field-level encryption beyond encrypted settings keys

## Must not build yet (next phases)

- Business module workflows and domain APIs
- External integrations beyond foundation LDAP/SMTP
- Multi-tenant SaaS billing or cross-org admin console
- Replacing `is_admin` flag-only access (roles are canonical for new users)

## Run commands

```bat
call scripts\set_env.local.bat
START_SOLACE.bat
```

- API: http://127.0.0.1:8080  
- UI: http://localhost:5173  

## Migration command

```bat
call scripts\set_env.local.bat
backend\venv\Scripts\python.exe -m alembic -c alembic.ini upgrade head
```

Current head: `003_foundation_completion`

## Acceptance check command

```bat
call scripts\set_env.local.bat
REM Start API first for HTTP checks
backend\venv\Scripts\python.exe scripts\foundation_acceptance_check.py
```

Optional env for login checks: `SOLACE_ADMIN_USER`, `SOLACE_ADMIN_PASSWORD`, `SOLACE_ADMIN_MFA_OTP`  
When admin MFA blocks HTTP login, the script issues an acceptance session token (same JWT path as normal login) to verify protected endpoints; confirm interactive login in the UI separately.

## Unit tests

```bat
cd backend
set PYTHONPATH=%CD%
venv\Scripts\python.exe -m unittest tests.test_rbac_tenant -v
```

## Known limitations

- Page route guard shows Access Denied; API still returns 403 for unauthorized API calls
- `is_admin=true` users receive wildcard `*` permissions (legacy bootstrap)
- RFI answer UI not separately permission-gated beyond API
- Acceptance script requires API running for HTTP endpoint checks
- Windows/SQL Server + ODBC 18 required; no SQLite

## Next recommended phase

See [FOUNDATION_V1_ACCEPTANCE_REPORT.md](./FOUNDATION_V1_ACCEPTANCE_REPORT.md#next-recommended-phase) for the full phased plan. Summary:

1. **Phase 2** — MFA/SMTP/LDAP staging validation; role-only access migration; SQL Server integration tests  
2. **Phase 3** — First business module (e.g. Document Hub) behind module enable flag
